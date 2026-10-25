#define UNICODE
#define _UNICODE
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shobjidl.h>
#include <shlwapi.h>
#include <string>
#include <vector>
#include <new>
#include <algorithm>

// {D4E07230-5AF0-4E95-A8A0-80D732CC1791}
static const CLSID CLSID_WinCip = {0xd4e07230,0x5af0,0x4e95,{0xa8,0xa0,0x80,0xd7,0x32,0xcc,0x17,0x91}};
static HMODULE module;
static volatile LONG objects = 0;
static std::wstring executable() {
    wchar_t path[32768];
    DWORD n = GetModuleFileNameW(module, path, 32768);
    if (!n || n == 32768) return L"";
    std::wstring result(path, n);
    return result.substr(0, result.find_last_of(L"\\/") + 1) + L"WinCip.exe";
}
static HRESULT copy(const std::wstring& text, PWSTR* out) {
    if (!out) return E_POINTER;
    *out = static_cast<PWSTR>(CoTaskMemAlloc((text.size()+1)*sizeof(wchar_t)));
    if (!*out) return E_OUTOFMEMORY;
    memcpy(*out, text.c_str(), (text.size()+1)*sizeof(wchar_t));
    return S_OK;
}
static std::wstring quote(const std::wstring& text) {
    std::wstring out = L"\"";
    size_t slashes = 0;
    for (wchar_t c : text) {
        if (c == L'\\') { ++slashes; continue; }
        if (c == L'"') out.append(slashes*2+1, L'\\');
        else out.append(slashes, L'\\');
        out += c;
        slashes = 0;
    }
    out.append(slashes*2, L'\\');
    return out + L"\"";
}
static std::vector<std::wstring> paths(IShellItemArray* items) {
    std::vector<std::wstring> result;
    DWORD count = 0;
    if (!items || FAILED(items->GetCount(&count))) return result;
    for (DWORD i = 0; i < count; ++i) {
        IShellItem* item = nullptr;
        if (FAILED(items->GetItemAt(i, &item))) return {};
        PWSTR path = nullptr;
        HRESULT hr = item->GetDisplayName(SIGDN_FILESYSPATH, &path);
        item->Release();
        if (FAILED(hr)) return {};
        result.emplace_back(path);
        CoTaskMemFree(path);
    }
    return result;
}
static bool archive(const std::wstring& path) {
    std::wstring ext = PathFindExtensionW(path.c_str());
    std::transform(ext.begin(), ext.end(), ext.begin(), towlower);
    const wchar_t* supported[] = {L".zip",L".rar",L".7z",L".tar",L".gz",L".bz2",L".xz",L".tgz",L".tbz2",L".txz",L".001"};
    return std::any_of(std::begin(supported), std::end(supported), [&](const wchar_t* s){return ext == s;});
}
static bool archives(IShellItemArray* items) {
    DWORD count = 0;
    if (!items || FAILED(items->GetCount(&count))) return false;
    for (DWORD index = 0; index < count; ++index) {
        IShellItem* item = nullptr;
        if (FAILED(items->GetItemAt(index, &item))) return false;
        SFGAOF attributes = 0;
        HRESULT result = item->GetAttributes(SFGAO_FOLDER | SFGAO_STREAM, &attributes);
        item->Release();
        // Windows exposes ZIPs as folders that also supply a file stream.
        if (FAILED(result) || ((attributes & SFGAO_FOLDER) && !(attributes & SFGAO_STREAM))) return false;
    }
    auto selected = paths(items);
    return !selected.empty() && std::all_of(selected.begin(), selected.end(), archive);
}
static std::wstring folder_name(std::wstring path) {
    path = PathFindFileNameW(path.c_str());
    auto extension = std::wstring(PathFindExtensionW(path.c_str()));
    if (extension.size() >= 4 && extension[0] == L'.' &&
        std::all_of(extension.begin()+1, extension.end(), [](wchar_t c){return c >= L'0' && c <= L'9';}))
        path.resize(path.size()-extension.size());
    auto lower = path;
    std::transform(lower.begin(), lower.end(), lower.begin(), towlower);
    const wchar_t* suffixes[] = {L".tar.gz",L".tar.bz2",L".tar.xz",L".7z.001",L".zip.001"};
    for (auto suffix : suffixes) {
        size_t length = wcslen(suffix);
        if (lower.size() > length && lower.compare(lower.size()-length,length,suffix) == 0)
            return path.substr(0,path.size()-length);
    }
    auto pos = path.find_last_of(L'.');
    if (pos != std::wstring::npos) path.resize(pos);
    auto folded = path;
    std::transform(folded.begin(), folded.end(), folded.begin(), towlower);
    pos = folded.rfind(L".part");
    if (pos != std::wstring::npos && pos+5 < folded.size() &&
        std::all_of(folded.begin()+pos+5, folded.end(), [](wchar_t c){return c >= L'0' && c <= L'9';}))
        path.resize(pos);
    return path;
}

class Command;
class Enumerator final : public IEnumExplorerCommand {
    LONG refs = 1;
    ULONG position = 0;
public:
    Enumerator(ULONG pos = 0) : position(pos) { InterlockedIncrement(&objects); }
    ~Enumerator() { InterlockedDecrement(&objects); }
    HRESULT STDMETHODCALLTYPE QueryInterface(REFIID iid, void** out) override {
        if (!out) return E_POINTER;
        *out = nullptr;
        if (iid == IID_IUnknown || iid == IID_IEnumExplorerCommand) {
            *out = static_cast<IEnumExplorerCommand*>(this); AddRef(); return S_OK;
        }
        return E_NOINTERFACE;
    }
    ULONG STDMETHODCALLTYPE AddRef() override { return InterlockedIncrement(&refs); }
    ULONG STDMETHODCALLTYPE Release() override { ULONG n = InterlockedDecrement(&refs); if (!n) delete this; return n; }
    HRESULT STDMETHODCALLTYPE Next(ULONG count, IExplorerCommand** output, ULONG* fetched) override;
    HRESULT STDMETHODCALLTYPE Skip(ULONG count) override { auto left = 5-position; position += std::min(count,left); return count <= left ? S_OK : S_FALSE; }
    HRESULT STDMETHODCALLTYPE Reset() override { position = 0; return S_OK; }
    HRESULT STDMETHODCALLTYPE Clone(IEnumExplorerCommand** out) override {
        if (!out) return E_POINTER;
        *out = new(std::nothrow) Enumerator(position);
        return *out ? S_OK : E_OUTOFMEMORY;
    }
};

class Command final : public IExplorerCommand {
    LONG refs = 1;
    int action;
public:
    Command(int kind = -1) : action(kind) { InterlockedIncrement(&objects); }
    ~Command() { InterlockedDecrement(&objects); }
    HRESULT STDMETHODCALLTYPE QueryInterface(REFIID iid, void** out) override {
        if (!out) return E_POINTER;
        *out = nullptr;
        if (iid == IID_IUnknown || iid == IID_IExplorerCommand) {
            *out = static_cast<IExplorerCommand*>(this); AddRef(); return S_OK;
        }
        return E_NOINTERFACE;
    }
    ULONG STDMETHODCALLTYPE AddRef() override { return InterlockedIncrement(&refs); }
    ULONG STDMETHODCALLTYPE Release() override { ULONG n = InterlockedDecrement(&refs); if (!n) delete this; return n; }
    HRESULT STDMETHODCALLTYPE GetTitle(IShellItemArray* items, PWSTR* title) override {
        if (action == -1) return copy(L"WinCip Compresor", title);
        if (action == 0) return copy(L"Abrir con WinCip Compresor", title);
        if (action == 1) return copy(L"Extraer archivos…", title);
        if (action == 2) {
            auto selected = paths(items);
            if (selected.size() == 1) return copy(L"Extraer en «" + folder_name(selected[0]) + L"»", title);
            return copy(L"Extraer cada comprimido en su carpeta", title);
        }
        if (action == 3) return copy(L"Extraer aquí", title);
        return copy(L"Añadir a un comprimido…", title);
    }
    HRESULT STDMETHODCALLTYPE GetIcon(IShellItemArray*, PWSTR* icon) override { return copy(executable() + L",0", icon); }
    HRESULT STDMETHODCALLTYPE GetToolTip(IShellItemArray*, PWSTR* text) override { if (!text) return E_POINTER; *text=nullptr; return E_NOTIMPL; }
    HRESULT STDMETHODCALLTYPE GetCanonicalName(GUID* name) override {
        if (!name) return E_POINTER;
        *name = CLSID_WinCip;
        name->Data4[7] += action+1;
        return S_OK;
    }
    HRESULT STDMETHODCALLTYPE GetState(IShellItemArray* items, BOOL, EXPCMDSTATE* state) override {
        if (!state) return E_POINTER;
        *state = ECS_HIDDEN;
        auto selected = paths(items);
        if (selected.empty()) return S_OK;
        bool compressed = archives(items);
        if (action == -1 || (action == 4 && !compressed) ||
            (compressed && action != 4 && (action != 0 || selected.size()==1))) *state = ECS_ENABLED;
        return S_OK;
    }
    HRESULT STDMETHODCALLTYPE Invoke(IShellItemArray* items, IBindCtx*) override {
        try {
            if (action < 0) return E_NOTIMPL;
            auto selected = paths(items);
            if (selected.empty()) return E_INVALIDARG;
            auto exe = executable();
            std::wstring args = quote(exe);
            const wchar_t* switches[] = {L"",L" --extract",L" --extract-folder",L" --extract-here",L" --compress"};
            args += switches[action];
            for (const auto& item : selected) args += L" " + quote(item);
            if (args.size() >= 32767) return HRESULT_FROM_WIN32(ERROR_FILENAME_EXCED_RANGE);
            STARTUPINFOW startup = {sizeof(startup)};
            PROCESS_INFORMATION process = {};
            if (!CreateProcessW(exe.c_str(), &args[0], nullptr, nullptr, FALSE, 0, nullptr, nullptr, &startup, &process))
                return HRESULT_FROM_WIN32(GetLastError());
            CloseHandle(process.hThread); CloseHandle(process.hProcess);
            return S_OK;
        } catch (...) { return E_OUTOFMEMORY; }
    }
    HRESULT STDMETHODCALLTYPE GetFlags(EXPCMDFLAGS* flags) override {
        if (!flags) return E_POINTER;
        *flags = action == -1 ? ECF_HASSUBCOMMANDS : ECF_DEFAULT;
        return S_OK;
    }
    HRESULT STDMETHODCALLTYPE EnumSubCommands(IEnumExplorerCommand** out) override {
        if (!out) return E_POINTER;
        *out = nullptr;
        if (action != -1) return E_NOTIMPL;
        *out = new(std::nothrow) Enumerator();
        return *out ? S_OK : E_OUTOFMEMORY;
    }
};
HRESULT Enumerator::Next(ULONG count, IExplorerCommand** output, ULONG* fetched) {
    if (!output || (!fetched && count != 1)) return E_POINTER;
    ULONG n = 0;
    while (n < count && position < 5) {
        auto command = new(std::nothrow) Command(position);
        if (!command) { if (fetched) *fetched = n; return E_OUTOFMEMORY; }
        output[n++] = command; ++position;
    }
    if (fetched) *fetched = n;
    return n == count ? S_OK : S_FALSE;
}
class Factory final : public IClassFactory {
    LONG refs = 1;
public:
    Factory() { InterlockedIncrement(&objects); }
    ~Factory() { InterlockedDecrement(&objects); }
    HRESULT STDMETHODCALLTYPE QueryInterface(REFIID iid, void** out) override {
        if (!out) return E_POINTER;
        *out=nullptr;
        if (iid == IID_IUnknown || iid == IID_IClassFactory) { *out=static_cast<IClassFactory*>(this); AddRef(); return S_OK; }
        return E_NOINTERFACE;
    }
    ULONG STDMETHODCALLTYPE AddRef() override { return InterlockedIncrement(&refs); }
    ULONG STDMETHODCALLTYPE Release() override { ULONG n=InterlockedDecrement(&refs); if (!n) delete this; return n; }
    HRESULT STDMETHODCALLTYPE CreateInstance(IUnknown* outer, REFIID iid, void** out) override {
        if (!out) return E_POINTER;
        *out=nullptr;
        if (outer) return CLASS_E_NOAGGREGATION;
        auto command = new(std::nothrow) Command();
        if (!command) return E_OUTOFMEMORY;
        HRESULT hr=command->QueryInterface(iid,out); command->Release(); return hr;
    }
    HRESULT STDMETHODCALLTYPE LockServer(BOOL lock) override { if(lock) InterlockedIncrement(&objects); else InterlockedDecrement(&objects); return S_OK; }
};
extern "C" __declspec(dllexport) HRESULT __stdcall DllGetClassObject(REFCLSID clsid, REFIID iid, void** out) {
    if (!out) return E_POINTER;
    *out=nullptr;
    if (clsid != CLSID_WinCip) return CLASS_E_CLASSNOTAVAILABLE;
    auto factory = new(std::nothrow) Factory();
    if (!factory) return E_OUTOFMEMORY;
    HRESULT hr=factory->QueryInterface(iid,out); factory->Release(); return hr;
}
extern "C" __declspec(dllexport) HRESULT __stdcall DllCanUnloadNow() { return objects == 0 ? S_OK : S_FALSE; }
BOOL WINAPI DllMain(HINSTANCE instance, DWORD reason, LPVOID) { if(reason==DLL_PROCESS_ATTACH) {module=instance; DisableThreadLibraryCalls(instance);} return TRUE; }
