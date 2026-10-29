#include <Windows.h>
#include <stdexcept>

#include <RxHook/API_DEF.h>
#include <RxHook/Hook.h>

static Rut::RxHook::Fn_MessageBoxW sg_fnMessageBoxW = MessageBoxW;

INT __stdcall MessageBoxW_Hook(HWND hWnd, LPCWSTR lpText, LPCWSTR lpCaption, UINT uType)
{
	lpText = L"My Hook";
	return sg_fnMessageBoxW(hWnd, lpText, lpCaption, uType);
}

static void StartHook(HMODULE hDllBase)
{
	::MessageBoxW(NULL, L"Inject DLL!", NULL, NULL);
	Rut::RxHook::Detours::AttrachDirectly(&sg_fnMessageBoxW, MessageBoxW_Hook);
}

BOOL APIENTRY DllMain(HMODULE hModule, DWORD  ul_reason_for_call, LPVOID lpReserved)
{
	switch (ul_reason_for_call)
	{
	case DLL_PROCESS_ATTACH:
		StartHook(hModule);
		break;
	case DLL_THREAD_ATTACH:
		break;
	case DLL_THREAD_DETACH:
		break;
	case DLL_PROCESS_DETACH:
		break;
	}
	return TRUE;
}

extern "C" VOID __declspec(dllexport) Dir_A() {}