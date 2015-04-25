//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////
//
// Quick'n'dirty ZX Spectrum 48K emulator
//
//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////

#include <stdlib.h>
#include <locale.h>
#include <stdio.h>
#include <vector>
#include "Z80.h"
#include <SDL.h>

//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////

static uint8_t g_z80_mem[65536];

struct LogEntry
{
    uint8_t f,a,c,b,e,d,l,h;
    uint8_t f2,a2,c2,b2,e2,d2,l2,h2;
    uint8_t ixl,ixh,iyl,iyh,spl,sph,pcl,pch;
    uint8_t i,iff1,iff2;
} __attribute__((packed));

static_assert(sizeof(LogEntry)==27,"");

static FILE *g_log_file;
static std::vector<LogEntry> g_log_entries;

static bool g_quit;

static const char ROM_FILE_NAME[]="48.rom";

//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////

struct SpectrumKey
{
    SDL_Scancode pc_scan_code;
    int row,col;
};

#define S(X) SDL_SCANCODE_##X

static uint8_t g_spectrum_keys_up[8];//[row]

static const SpectrumKey g_spectrum_keys_table[]={
    {S(LSHIFT),0,0},{S(Z),0,1},{S(X),0,2},{S(C),0,3},{S(V),0,4},
    {S(A),1,0},{S(S),1,1},{S(D),1,2},{S(F),1,3},{S(G),1,4},
    {S(Q),2,0},{S(W),2,1},{S(E),2,2},{S(R),2,3},{S(T),2,4},
    {S(1),3,0},{S(2),3,1},{S(3),3,2},{S(4),3,3},{S(5),3,4},
    {S(0),4,0},{S(9),4,1},{S(8),4,2},{S(7),4,3},{S(6),4,4},
    {S(P),5,0},{S(O),5,1},{S(I),5,2},{S(U),5,3},{S(Y),5,4},
    {S(RETURN),6,0},{S(L),6,1},{S(K),6,2},{S(J),6,3},{S(H),6,4},
    {S(SPACE),7,0},{S(RSHIFT),7,1},{S(M),7,2},{S(N),7,3},{S(B),7,4},
    {SDL_SCANCODE_UNKNOWN}
};

#undef S

static const SpectrumKey *g_spectrum_keys[SDL_NUM_SCANCODES];

//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////

static void InitKeys()
{
    for(const SpectrumKey *sk=g_spectrum_keys_table;sk->pc_scan_code!=SDL_SCANCODE_UNKNOWN;++sk)
	g_spectrum_keys[sk->pc_scan_code]=sk;

    memset(g_spectrum_keys_up,255,sizeof g_spectrum_keys_up);
}

//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////

static void LoadROM()
{
    FILE *f=fopen(ROM_FILE_NAME,"rb");
    if(!f)
    {
	fprintf(stderr,"FATAL: failed to open ROM file: %s\n",ROM_FILE_NAME);
	exit(1);
    }

    if(fread(g_z80_mem,1,16384,f)!=16384)
    {
	fprintf(stderr,"FATAL: failed to load 16K from ROM file: %s\n",ROM_FILE_NAME);
	exit(1);
    }

    fclose(f);
    f=0;
}

static void RedrawScreen(SDL_Texture *texture)
{
    uint8_t pixels[192][256];
    
    for(int y=0;y<192;++y)
    {
	uint16_t addr=0x4000+((y&7)<<8)+(((y>>3)&7)<<5)+((y>>6)<<11);
	
	uint8_t *p=pixels[y];
	
	for(int x=0;x<32;++x)
	{
	    uint v=g_z80_mem[addr+x];

	    *p++=(v&0x80)?255:0;
	    *p++=(v&0x40)?255:0;
	    *p++=(v&0x20)?255:0;
	    *p++=(v&0x10)?255:0;
	    *p++=(v&0x08)?255:0;
	    *p++=(v&0x04)?255:0;
	    *p++=(v&0x02)?255:0;
	    *p++=(v&0x01)?255:0;
	}
    }

    SDL_UpdateTexture(texture,nullptr,pixels,sizeof pixels[0]);
}

//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////

static void LogZ80State(const Z80 *z)
{
    if(!g_log_file)
	return;
	
    // f a c b e d l h
    // f' a' c' b' e' d' l' h'
    // IXl IXh IYl IYh SPl SPh PCl PCh

    g_log_entries.emplace_back();
    LogEntry *save=&g_log_entries.back();
    
    save->f=z->AF.B.l;
    save->a=z->AF.B.h;
    save->c=z->BC.B.l;
    save->b=z->BC.B.h;
    save->e=z->DE.B.l;
    save->d=z->DE.B.h;
    save->l=z->HL.B.l;
    save->h=z->HL.B.h;
    save->f2=z->AF1.B.l;
    save->a2=z->AF1.B.h;
    save->c2=z->BC1.B.l;
    save->b2=z->BC1.B.h;
    save->e2=z->DE1.B.l;
    save->d2=z->DE1.B.h;
    save->l2=z->HL1.B.l;
    save->h2=z->HL1.B.h;
    save->ixl=z->IX.B.l;
    save->ixh=z->IX.B.h;
    save->iyl=z->IY.B.l;
    save->iyh=z->IY.B.h;
    save->spl=z->SP.B.l;
    save->sph=z->SP.B.h;
    save->pcl=z->PC.B.l;
    save->pch=z->PC.B.h;
    save->i=z->I;
    save->iff1=!!(z->IFF&IFF_1);
    save->iff2=!!(z->IFF&IFF_2);
}

static void FlushLog()
{
    if(g_log_entries.empty())
	return;

    if(!g_log_file)
	return;

    fwrite(&g_log_entries[0],sizeof g_log_entries[0],g_log_entries.size(),g_log_file);
    g_log_entries.clear();
}

static void CloseLogFile()
{
    if(g_log_file)
    {
	fclose(g_log_file);
	g_log_file=nullptr;
    }
}

//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////

void WrZ80(register word Addr,register byte Value)
{
    if(Addr>=0x4000)
	g_z80_mem[Addr]=Value;
}

//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////

byte RdZ80(register word Addr)
{
    return g_z80_mem[Addr];
}

//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////

void OutZ80(register word Port,register byte Value)
{
    //printf("OUT: Port=%04X Value=%02X\n",Port,Value);
}

//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////

byte InZ80(register word Port)
{
    uint8_t val=255;
    
    if((Port&0xff)==0xfe)
    {
	uint8_t sel=Port>>8;
	
	for(int row=0;row<8;++row)
	{
	    if(!(sel&(1<<row)))
		val&=g_spectrum_keys_up[row];
	}
	
	// FE 1111 1110
	// FD 1111 1101
	// FB 1111 1011
	// F7 1111 0111
	// EF 1110 1111
	// DF 1101 1111
	// BF 1011 1111
	// 7F 0111 1111
    }

    //printf("IN: Port=%04X: Result=%02X\n",Port,val);
    
    return val;
}
//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////

word LoopZ80(register Z80 *R)
{
    if(g_quit)
	return INT_QUIT;
    else
	return INT_NONE;
}

//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////

void PatchZ80(register Z80 *R)
{
}

//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////

byte DebugZ80(register Z80 *R)
{
    // Do this from DebugZ80, not from the main loop!
    //
    // EI resets the Z80 cycle counter and will therefore run another
    // instruction.
    LogZ80State(R);
    return 1;
}

//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////

static void UpdateKeyFlag(const SDL_Keysym &k,bool pressed)
{
    const SpectrumKey *sk=g_spectrum_keys[k.scancode];
    if(!sk)
	return;

    uint8_t *v=&g_spectrum_keys_up[sk->row];

    uint8_t mask=1<<sk->col;

    bool changed=false;
    if(pressed)
    {
	if(*v&mask)
	    changed=true;
	
	*v&=~mask;
    }
    else
    {
	if(!(*v&mask))
	    changed=true;
	
	*v|=mask;
    }

    // if(changed)
    // 	printf("%s: new state: %s\n",SDL_GetScancodeName(k.scancode),pressed?"DOWN":"UP");
    
}

static bool HandleSDLEvents()
{
    SDL_Event e;
    while(SDL_PollEvent(&e))
    {
	switch(e.type)
	{
	case SDL_KEYDOWN:
	case SDL_KEYUP:
	    {
		UpdateKeyFlag(e.key.keysym,e.key.state==SDL_PRESSED);
	    }
	    break;

	case SDL_QUIT:
	    return false;

	case SDL_WINDOWEVENT:
	    {
	    }
	    break;
	}
    }

    return true;
}

int main(int argc,char *argv[])
{
    LoadROM();
    InitKeys();

    SDL_Init(SDL_INIT_VIDEO|SDL_INIT_TIMER);

    SDL_Window *main_window=SDL_CreateWindow("Q'n'D Emu",
					     SDL_WINDOWPOS_UNDEFINED,SDL_WINDOWPOS_UNDEFINED,
					     512,384,
					     SDL_WINDOW_RESIZABLE);
    

    //SDL_Surface *main_window_surface=SDL_GetWindowSurface(main_window);

    SDL_Renderer *renderer=SDL_CreateRenderer(main_window,-1,0);

    SDL_Texture *back_buffer=SDL_CreateTexture(renderer,
					       SDL_PIXELFORMAT_RGB332,
					       SDL_TEXTUREACCESS_STREAMING,
					       256,192);

    g_log_file=fopen("z80_log.dat","wb");
    atexit(&CloseLogFile);

    if(g_log_file)
    {z
	// Log file version.
	fputc(3,g_log_file);

	// Index for first instruction.
	for(int i=0;i<4;++i)
	    fputc(0,g_log_file);
    }
    
    Z80 z80_state;
    memset(&z80_state,0,sizeof z80_state);
    ResetZ80(&z80_state);
    z80_state.Trace=1;

    // int num_redraws=0;
    // int num_instrs=0;
    // bool step=false;

    uint64_t ticks_per_frame=SDL_GetPerformanceFrequency()/50;
    uint64_t ticks_per_ms=SDL_GetPerformanceFrequency()/1000;

    int num_cycles_left=0;
    
    while(HandleSDLEvents())
    {
	uint64_t next_vsync=SDL_GetPerformanceCounter()+ticks_per_frame;

	int line=0;
	while(line<625)
	{
	    num_cycles_left=ExecZ80(&z80_state,num_cycles_left+112);
	    if(num_cycles_left<=0)
	    {
		++line;

		if(line==256*2)
		    IntZ80(&z80_state,255);
	    }
	}

	RedrawScreen(back_buffer);

	SDL_RenderCopy(renderer,back_buffer,nullptr,nullptr);
	
	SDL_RenderPresent(renderer);

	FlushLog();

	// make the emulated Spectrum run at ~50Hz without mashing the
	// CPU...
	for(;;)
	{
	    uint64_t now=SDL_GetPerformanceCounter();
	    if(now>=next_vsync)
		break;

	    if(next_vsync-now>2*ticks_per_ms)
		SDL_Delay(1);
	}
    }

    SDL_Quit();

    return 0;
}
