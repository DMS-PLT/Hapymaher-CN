#include <iostream>
#include "Rut/RxJson.h"


int main(int argc, char* argv[])
{
	Rut::RxJson::JArray json = Rut::RxJson::Parser{}.Load(L"1.json");
	Rut::RxJson::Parser{}.Save(json, L"2.json", true, false);
}