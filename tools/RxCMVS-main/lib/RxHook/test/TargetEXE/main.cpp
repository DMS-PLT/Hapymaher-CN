#include <Windows.h>


int main()
{
	while (true)
	{
		::MessageBoxW(NULL, L"Hook This....", NULL, NULL);
	}
}