#include <stdexcept>
#include <Windows.h>

#include <RxHook/Hook.h>


INT APIENTRY WinMain(_In_ HINSTANCE hInstance, _In_opt_ HINSTANCE hPrevInstance, _In_ LPSTR lpCmdLine, _In_ int nShowCmd)
{
	STARTUPINFOW si = { 0 };
	PROCESS_INFORMATION pi = { 0 };
	si.cb = sizeof(si);

	try
	{
		const char* dll_name_array[1] = { "SampleDLL.dll" };
		if (Rut::RxHook::CreateProcessWithDlls(L"TargetEXE.exe", CREATE_SUSPENDED, 1, dll_name_array, &si, &pi))
		{
			if (pi.hThread)
			{
				ResumeThread(pi.hThread);
				CloseHandle(pi.hThread);
				CloseHandle(pi.hProcess);
			}
		}
		else
		{
			MessageBoxW(NULL, L"DetourCreateProcessWithDll Failed!", NULL, MB_OK);
		}
	}
	catch (const std::runtime_error& err)
	{
		MessageBoxA(NULL, err.what(), NULL, NULL);
		exit(-1);
	}
}