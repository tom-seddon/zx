//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////
//
// Quick'n'dirty ZX Spectrum 48K emulator
//
//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////

#include <ncurses.h>
#include <stdlib.h>
#include <locale.h>
#include <stdio.h>
#include <vector>
#include "Z80.h"

//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////

static uint8_t g_z80_mem[65536];


struct LogEntry
{
    uint8_t f,a,c,b,e,d,l,h;
    uint8_t f2,a2,c2,b2,e2,d2,l2,h2;
    uint8_t ixl,ixh,iyl,iyh,spl,sph,pcl,pch;
};

static_assert(sizeof(LogEntry)==24,"");

static FILE *g_log_file;
static std::vector<LogEntry> g_log_entries;

static bool g_quit;

enum ColourPairs
{
    SPECTRUM_COLOURS=1,
    DEBUG_COLOURS,
};

static WINDOW *g_swin,*g_dwin;

static const char ROM_FILE_NAME[]="48.rom";

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

//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////

static void DoEndwin()
{
    endwin();
}

//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////

static void DeleteWindow(WINDOW **w)
{
    if(*w)
    {
	delwin(*w);
	*w=0;
    }
}

static void DeleteWindows()
{
    DeleteWindow(&g_swin);
    DeleteWindow(&g_dwin);
}

//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////

// static void wcls(WINDOW *win)
// {
//     int w,h;
//     getmaxyx(win,h,w);

//     //scrollok(win,FALSE);

//     for(int i=0;i<w*h;++i)
//     {
// 	//wprintw(win,"\xe2\x96\x98");
// 	wprintw(win,"FART");
//     }

//     //scrollok(win,TRUE);

//     //wmove(win,0,0);
//     //wclear(win);
// }

//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////

static void UpdateWindows()
{
    DeleteWindows();

    int w,h;
    getmaxyx(stdscr,h,w);

    if(w<128||h<128)
    {
	fprintf(stderr,"FATAL: screen must be at least 128x128.\n");
	fprintf(stderr,"FATAL: screen must be at least 128x110.\n");
	exit(1);
    }

    g_swin=newwin(96,w,0,0);
    g_dwin=newwin(h-96,w,96,0);

    scrollok(g_dwin,TRUE);
    scrollok(g_swin,FALSE);

    wattrset(g_swin,COLOR_PAIR(SPECTRUM_COLOURS));
    wattrset(g_dwin,COLOR_PAIR(DEBUG_COLOURS));

    wprintw(g_dwin,"Hello.\n");

    wrefresh(g_dwin);
    wrefresh(g_swin);
}

//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////

static const char *const BLOCK_CHARS[]={
    " ",
    "\xe2\x96\x9d",//1
    "\xe2\x96\x98",//2
    "\xe2\x96\x80",//3
    "\xe2\x96\x97",//4
    "\xe2\x96\x90",//5
    "\xe2\x96\x9a",//6
    "\xe2\x96\x9c",//7
    "\xe2\x96\x96",//8
    "\xe2\x96\x9e",//9
    "\xe2\x96\x8c",//10
    "\xe2\x96\x9b",//11
    "\xe2\x96\x84",//12
    "\xe2\x96\x9f",//13
    "\xe2\x96\x99",//14
    "\xe2\x96\x88",//15
};

static void RedrawScreen(int n)
{
    for(int y=0;y<192;y+=2)
    {
	uint16_t addr=0x4000+((y&7)<<8)+(((y>>3)&7)<<5)+((y>>6)<<11);
	
	const uint8_t *as=&g_z80_mem[addr+0x0000];
	const uint8_t *bs=&g_z80_mem[addr+0x0100];
	    
	wmove(g_swin,y/2,0);
	
	for(int x=0;x<32;++x)
	{
	    uint8_t a=as[x];
	    uint8_t b=bs[x];

	    uint8_t a76=a>>6,a54=(a>>4)&3,a32=(a>>2)&3,a10=a&3;
	    uint8_t b76=b>>6,b54=(b>>4)&3,b32=(b>>2)&3,b10=b&3;


	    uint8_t c0=(a76<<0)|(b76<<2);
	    uint8_t c1=(a54<<0)|(b54<<2);
	    uint8_t c2=(a32<<0)|(b32<<2);
	    uint8_t c3=(a10<<0)|(b10<<2);

	    wprintw(g_swin,"%s%s%s%s",BLOCK_CHARS[c0],BLOCK_CHARS[c1],BLOCK_CHARS[c2],BLOCK_CHARS[c3]);
	    //wprintw(g_swin,"%04X",g_z80_state.PC.W);
	}

	if(y==0)
	    wprintw(g_swin," %d",n);
	else if(y==2)
	    wprintw(g_swin," %zu",g_log_entries.size());
	
	//wprintw(g_swin," %d\n",n);
    }

    wrefresh(g_swin);
}

//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////

static void LogZ80State(const Z80 *z)
{
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
    wprintw(g_dwin,"OUT: Port=%04X Value=%02X\n",Port,Value);
    wrefresh(g_dwin);
}

//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////

byte InZ80(register word Port)
{
    wprintw(g_dwin,"IN: Port=%04X\n",Port);
    wrefresh(g_dwin);
    
    return 255;
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
    LogZ80State(R);
    
    return 1;
}

//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////

int main()
{
    LoadROM();
    
    setlocale(LC_ALL,"");
    initscr();
    atexit(&DoEndwin);

    g_log_file=fopen("z80_log.dat","wb");
    atexit(&CloseLogFile);

    if(g_log_file)
	fputc(1,g_log_file);	// version
    
    start_color();
    noecho();

    init_pair(DEBUG_COLOURS,COLOR_YELLOW,COLOR_BLUE);
    init_pair(SPECTRUM_COLOURS,COLOR_WHITE,COLOR_BLACK);

    UpdateWindows();

    Z80 z80_state;
    memset(&z80_state,0,sizeof z80_state);
    ResetZ80(&z80_state);

    int num_redraws=0;
    int num_instrs=0;
    bool step=false;
    
    for(;;)
    {
	ExecZ80(&z80_state,1);

	bool redraw=false;
	
	++num_instrs;
	if(num_instrs>10000)
	{
	    num_instrs=0;
	    redraw=true;
	    IntZ80(&z80_state,255);
	}

	if(step)
	    redraw=true;

	if(redraw)
	{
	    RedrawScreen(num_redraws++);
	    FlushLog();
	}

	if(z80_state.PC.W==0x120a)
	{
	    break;
	}

	if(step)
	{
	    const Z80 *z=&z80_state;
	    
	    wprintw(g_dwin,"%04X : AF =%04X BC =%04X DE =%04X HL =%04X  IX=%04X  PC=%04X\n",
		    z->PC.W,z->AF.W,z->BC.W,z->DE.W,z->HL.W,z->IX.W,z->PC.W);
	    wprintw(g_dwin,"       AF'=%04X BC'=%04X DE'=%04X HL'=%04X  IY=%04X  SP=%04X\n",
		    z->AF1.W,z->BC1.W,z->DE1.W,z->HL1.W,z->IY.W,z->SP.W);
	    
	    wrefresh(g_dwin);
	    wgetch(g_dwin);
	}
    }
}
