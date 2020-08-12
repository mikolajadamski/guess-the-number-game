import socket
import time
import re
import threading

#Kody Operacji i odpowiedzi
"""
DATA
1 - połącz (Operacja)
2 - połączono (Odpowiedz)
3 - w trakcie gry (Odpowiedz)
4 - start (Operacja)
5 - rozpoczęto grę (Odpowiedz)
6 - za mało graczy (Odpowiedz)
7 - zwycięzca (Operacja)
8 - koniec czasu (Odpowiedz)
9 - przegrałeś (Odpowiedz)
10 - liczba (Operacja)
11 - za wysoko (Odpowiedz)
12 - za nisko (Odpowiedz)
13 - trafiony (Odpowiedz)
14 - Czas (Operacja)
16 - rozłącz (Operacja)
17 - rozłączono (Odpowiedz)
18 - błąd (Operacja)
e1 - błąd wartości (Odpowiedz)
e2 - błąd rozkazu (Odpowiedz)
e3 - niezany błąd (Odpowiedz)
"""

#Adres IPv4 serwera oraz numer portu
IP_HOST=("192.168.1.71",20000)

#Okreslenie rodzaju klienta
client = socket.socket(socket.AF_INET #Internet
                                    ,socket.SOCK_DGRAM #Polaczenie UDP
                                                                     )
#Zbindowanie adresu IPv4 oraz numeru portu klienta
client.bind(("192.168.1.72", 20000))

#Zmienne globalne wykorzystywane w funkcjach: Operations oraz Play_Game
global Game_Over
global Game_Start
global Id
global recieved

#Funkcja wysylajaca dane do serwera
#Wywoływana przez użytkownika podczas rozpoczęcia rozgrywki i wysyłaniu liczb
def Send(NS,ID,OP,ANS,VAL):
    ZC = time.strftime("%Y,%b,%d,%H:%M:%S", time.localtime())
    if (NS == 2):
        client.sendto(bytes("NSekwencyjny=" + str(NS) + ";"
                      + "ZnacznikCzasu=" + ZC+ ";"
                      + "Identyfikator=" + ID + ";"
                      + "Operacja" + "=" + OP + ";", "utf-8"),
                      IP_HOST)
        client.sendto(bytes("NSekwencyjny=" + str(NS - 1) + ";"
                      + "ZnacznikCzasu=" + ZC + ";"
                      + "Identyfikator=" + ID + ";"
                      + "Odpowiedz" + "=" + ANS + ";", "utf-8"),
                      IP_HOST)
        client.sendto(bytes("NSekwencyjny=" + str(NS - 2) + ";"
                      + "ZnacznikCzasu=" + str(ZC) + ";"
                      + "Identyfikator=" + str(ID) + ";"
                      + "VAL" + "=" + VAL + ";", "utf-8"),
                      IP_HOST)
    elif (NS == 1):
        client.sendto(bytes("NSekwencyjny=" + str(NS) + ";"
                      + "ZnacznikCzasu=" + str(ZC) + ";"
                      + "Identyfikator=" + str(ID) + ";"
                      + "Operacja" + "=" + OP + ";", "utf-8"),
                      IP_HOST)
        client.sendto(bytes("NSekwencyjny=" + str(NS - 1) + ";"
                      + "ZnacznikCzasu=" + str(ZC) + ";"
                      + "Identyfikator=" + str(ID) + ";"
                      + "Odpowiedz" + "=" + str(ANS) + ";", "utf-8"),
                      IP_HOST)

#Funkcja odbierająca dane od serwera
#Wywoływana nabieżaco przez funkcję Operations
def Recv(Part):
    RecvData, Address = client.recvfrom(1024)
    RecvData = RecvData.decode()
    Part = make_part(RecvData)
    #print(Part)
    return Part

#Funkcja dzieląca otrzyamny pakiet danych na cześci
#Wywoływana po otrzymaniu pakietu w funcji Recv
def make_part(data, headers_dict={}):
    headers = re.findall("\w+=\w+;", data)
    for header in headers:
        headers_dict[(re.findall("(\w+)=", header))[0]] = (re.findall("=(\w+)", header))[0]
    return headers_dict

#Funkcja odpowiadająca za określenie kolejnych działań w zależności od otrzymanych danych
#Wwoływana nabieżąco przez wątek
def Operations():
    try:
        global Game_Start
        global Game_Over
        global Id
        while not Game_Over:
            Part = {}
            Part = Recv(Part)
            while int(Part["NSekwencyjny"])>0:
                Part = Recv(Part)
            #print(Part)
            Id = Part["Identyfikator"]
            if (Part["Odpowiedz"] == 'e1'):
                print("Musisz podać liczbę!")
            elif (Part["Odpowiedz"] == 'e2'):
                print("Błąd rozkazu")
            elif (Part["Odpowiedz"] == 'e3'):
                print("Nieznany błąd")
            elif Part["Operacja"] == '1':
                #Connect
                if Part["Odpowiedz"] == 'ok':
                    if Part["VAL"] == '2':
                         print("Polaczono z serwerem.\nIdentyfikator = " + Id + "\nPoczekalnia...")
                elif Part["Odpowiedz"] == '3':
                    print("Gra wlasnie trwa, sprobuj pozniej")
                    Game_Over = True
            elif Part["Operacja"] == "14":
                if Part["Odpowiedz"] == "ok":
                    print('Pozostały czas:',Part["VAL"])
            elif Part["Operacja"] == '4':
                if Part["Odpowiedz"] == '5':
                    print("Gra sie rozpoczyna")
                    Game_Start = True
                elif (Part["Odpowiedz"] == '6'):
                        print("Niewystarczajaca liczba graczy.\nKliknij aby wrocic do menu")
            elif Part["Operacja"] == "10":
                if (Part["Odpowiedz"] == '11'):
                    print("Za wysoko\nSprobuj ponownie")
                elif (Part["Odpowiedz"] == '12'):
                    print("Za nisko\nSpróbuj ponownie")
                elif (Part["Odpowiedz"] == '13'):
                    print("WYGRAŁEŚ!!!")
            elif Part["Operacja"] == '16':
                if Part["Odpowiedz"] == '17':
                    print("Rozłączono z serwerem. Wciśnij dowolną cyfre aby kontynuować.")
                    Game_Over = True
                    Game_Start = False
            elif Part["Operacja"] == '7':
                if Part["Odpowiedz"] == "8":
                        print("Koniec Czasu!")
                elif Part["Odpowiedz"] == "9":
                        print("Przegrałeś! Ktoś Cię ubiegł.")
    except ConnectionResetError:
        Game_Over = True
        print("Błąd połączenia")

#Fukcja wywołana przez użytkownika wysyłająca serwerowi chęc gry
def Play_Game():
    Send(1, 0, "1", "null", 0)
    t1 = threading.Thread(target=Operations)
    t1.start()
    while not Game_Over:
        if Game_Start:
            value = input("Strzelaj: ")
            if len(value)==0:
                print("Musisz coś wpisać!")
            elif not Game_Over:
                value = int(value)
                if value<0:
                    Send(1,Id,"16", "null", str(value))
                else:
                    Send(2,Id,"10","null",str(value))

#Czynności wyywoływane po uruchomieniu aplikacji
while True:
    print("1.Start game")
    print("2.Exit")
    choice = int(input("Choose operation: "))
    try:
        if choice==1:
            Game_Over = False
            Game_Start = False
            Play_Game()
        else:
            break
    except ConnectionResetError:
        print("Nie udalo sie polaczyc z serwerem!")
