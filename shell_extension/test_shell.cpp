#define UNICODE
#define _UNICODE
#include <windows.h>
#include <shobjidl.h>
#include <stdio.h>
#include <assert.h>
#include <string>
static const CLSID CLSID_WinCip={0xd4e07230,0x5af0,0x4e95,{0xa8,0xa0,0x80,0xd7,0x32,0xcc,0x17,0x91}};
int wmain(int argc,wchar_t**argv) {
    setbuf(stdout,nullptr);
    printf("start argc %d\n",argc);
    CoInitializeEx(nullptr,COINIT_APARTMENTTHREADED);
    IExplorerCommand* root=nullptr;
    HMODULE library=nullptr;
    HRESULT hr;
    if(argc>3) {
        library=LoadLibraryW(argv[3]);
        if(!library) return 4;
        using Entry=HRESULT(__stdcall*)(REFCLSID,REFIID,void**);
        auto entry=(Entry)GetProcAddress(library,"DllGetClassObject");
        IClassFactory* factory=nullptr;
        hr=entry(CLSID_WinCip,IID_PPV_ARGS(&factory));
        if(FAILED(hr)) return 5;
        hr=factory->CreateInstance(nullptr,IID_PPV_ARGS(&root));
        factory->Release();
    } else hr=CoCreateInstance(CLSID_WinCip,nullptr,CLSCTX_LOCAL_SERVER,IID_PPV_ARGS(&root));
    printf("Packaged COM activation: %08lx\n",(unsigned long)hr);
    if(FAILED(hr)) return 1;
    IShellItem* item=nullptr;
    hr=SHCreateItemFromParsingName(argv[1],nullptr,IID_PPV_ARGS(&item)); assert(SUCCEEDED(hr));
    printf("shell item %08lx %p\n",(unsigned long)hr,item);
    if (FAILED(hr)) return 2;
    IShellItemArray* items=nullptr;
    hr=SHCreateShellItemArrayFromShellItem(item,IID_PPV_ARGS(&items)); assert(SUCCEEDED(hr));
    printf("array %08lx %p\n",(unsigned long)hr,items);
    if(FAILED(hr)) return 3;
    item->Release();
    PWSTR title=nullptr; hr=root->GetTitle(items,&title); assert(SUCCEEDED(hr));
    wprintf(L"Root: %ls\n",title); CoTaskMemFree(title);
    EXPCMDFLAGS flags; root->GetFlags(&flags); assert(flags&ECF_HASSUBCOMMANDS);
    IEnumExplorerCommand* entries=nullptr; hr=root->EnumSubCommands(&entries); assert(SUCCEEDED(hr));
    int index=0;
    IExplorerCommand* child=nullptr;
    while(entries->Next(1,&child,nullptr)==S_OK) {
        title=nullptr; hr=child->GetTitle(items,&title); assert(SUCCEEDED(hr));
        EXPCMDSTATE state; hr=child->GetState(items,TRUE,&state); assert(SUCCEEDED(hr));
        wprintf(L"%d: %ls [%d]\n",index,title,(int)state);
        if(argc>4) {
            bool compressed=_wtoi(argv[4])!=0;
            assert(state == ((compressed && index<4) || (!compressed && index==4) ? ECS_ENABLED : ECS_HIDDEN));
        }
        if(argc>2 && _wtoi(argv[2])==index) { hr=child->Invoke(items,nullptr); printf("Invoke: %08lx\n",(unsigned long)hr); assert(SUCCEEDED(hr)); }
        CoTaskMemFree(title); child->Release(); ++index;
    }
    assert(index==5);
    entries->Reset(); entries->Skip(2);
    IEnumExplorerCommand* clone=nullptr; assert(SUCCEEDED(entries->Clone(&clone)));
    assert(clone->Next(1,&child,nullptr)==S_OK); child->Release(); clone->Release();
    entries->Release(); items->Release(); root->Release(); CoUninitialize(); if(library) FreeLibrary(library);
    return 0;
}
