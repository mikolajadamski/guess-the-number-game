import socket
import time
import re
import random
import collections
import threading

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


class GameOfNumbers:
    """
    Klasa zawierająca wszystkie funkcje oraz zmienne serwera.

    """
    client_list: dict = collections.OrderedDict ()
    id_seed = 1
    PORT = 20000
    SERVER_IP = "192.168.1.71"
    s = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    s.bind((SERVER_IP, PORT))
    gametime = 0
    starttime = 0
    threadstopper = False
    isguessed = False
    err = False
    number = 0

    def collect_players(self, players=3):
        """
        :param players: liczba graczy na ilu serwer ma czekać(domyślnie trzech).
        Serwer czeka 40 sekund na graczy. Wysyła graczom informacje
        czy gra się rozpoczyna czy nie.
        :return: true lub false, w zależności czy uda zebrać się wymaganą liczbe graczy
        (true - udało się, false - nie udało się)
        """
        print("Oczekiwanie na graczy: ")
        tim = time.time()
        waittim = 40
        start = True
        self.client_list = collections.OrderedDict()
        while len(self.client_list) < players:
            t1 = threading.Thread(target=self.counttime)
            self.threadstopper = False
            t1.start()
            data, address = self.recieve()
            headers = self.parse_headers(data)
            while int(headers["NSekwencyjny"]) > 0:
                data, address1 = self.recieve()
                headers = self.parse_headers(data)
            if headers["Operacja"] == "1":
                self.connect (headers, address, tim)
            elif headers["Operacja"] == "timeout":
                if address[0] == self.SERVER_IP:
                    start = False
                    break

                else:
                    break
            else:
                self.send (1, headers["Identyfikator"], headers["Operacja"], "1", address)
                self.send (0, headers["Identyfikator"], "Odpowiedz", "e2", address)
        self.threadstopper = True
        if start:
            game = "5"
        else:
            game = "6"
        for clientid, clientaddress in self.client_list.items():
            self.send(1, clientid, "Operacja", "4", clientaddress)
            self.send(0, clientid, "Odpowiedz", game, clientaddress)
            if not start:
                self.send(1, clientid, "Operacja", "16", clientaddress)
                self.send(0, clientid, "Odpowiedz", "17", clientaddress)
        if not start:
            self.client_list = collections.OrderedDict()
            print("Nie udało się zebrać wystarczającej liczby...")
        return start

    def recieve(self):
        """
        Odbiera wiadomości i je dekoduje oraz drukuje.
        :return: wiadomość oraz adres nadawcy
        """
        data, address = self.s.recvfrom (1024)
        data = data.decode ()
        print(data + " from ", address)
        return data, address

    def send(self, ns: int, id, msg: str, val: str, clientaddress):
        """
        :param ns: Numer sekwencyjny wiadomości
        :param id: Identyfikator odbiorcy
        :param msg: rodzaj wiadomości (np: Operacja/Odpowiedź/Wartość)
        :param val: treść wiadomości (np: nr operacji/status/ilość sekund)
        :param clientaddress: adres odbiorcy (IP i port)
        Wysyłanie wiadomości zawierającymi podane dane i drukowanie tej wiadomości.
        Każda wiadomość zawiera numer sekwencyjny, znacznik czasu oraz Identyfikator
        """
        msg = "NSekwencyjny=" + str (ns) + ";ZnacznikCzasu=" + time.strftime ("%Y,%b,%d,%H:%M:%S", time.localtime ()) + \
              ";Identyfikator=" + str (id) + ";" + msg + "=" + val + ";"
        self.s.sendto (bytes (msg, "utf-8"), clientaddress)
        print("Wyslano " + msg + " do", clientaddress)

    def counttime(self, val=1):
        """
        :param val: 1 - poczekalnia - odlicza 40 sekund i przerywa nasłuchiwanie,
                    0 - gra - odlicza czas do końca gry i przerywa nasłuchiwanie
        przerwanie nasłuchiwania realizowane jest poprzez wysłanie operacji
        timeout do samego siebie (aby zwolnić wątek nasłuchujący)
        """
        tm = time.time ()
        if val:
            def statement():
                return time.time() - tm > 40
        else:
            def statement():
                return self.gametime - (time.time () - self.starttime) < 0
        while not self.threadstopper:
            if statement():
                self.send(0, "server", "Operacja", "timeout",
                           (self.SERVER_IP, self.PORT))
                self.threadstopper = True
            else:
                continue

    def parse_headers(self, data, headers_dict={}):
        """
        :param data: treść otrzymanej wiadomości
        :param headers_dict: słownik par klucz=wartość (domyślnie pusty słownik)
        za pomocą biblioteki regex wydobywa z wiadomości istotne dane i zapisuje
        w słowniku
        :return: słownik par klucz=wartość
        """
        headers = re.findall("\w+=\w+;", data)
        for header in headers:
            headers_dict[(re.findall("(\w+)=", header))[0]] = (re.findall("=(\w+)", header))[0]
        return headers_dict

    def connect(self, headers, address, tim):
        """
        :param headers: dane z wiadomości
        :param address: adres klienta
        :param tim: czas rozpoczęcia odliczania w poczekalni
        dodaje nowego klienta do listy klientów, wysyła potwierdzenie dodania oraz
        czas do końca poczekalni
        """
        if int (headers["Identyfikator"]) not in self.client_list:
            id = self.generate_id()
            self.client_list[id] = address
            self.send(1, id, "Operacja", "1", address)
            self.send(0, id, "Odpowiedz", "2", address)
            self.send(2, id, "Operacja", "14", address)
            self.send(1, id, "Odpowiedz", "ok", address)
            self.send(0, id, "VAL", str(int(40 - (time.time() - tim))), address)
            print("Player Id =", id, "connected")
        else:
            self.send(1, headers["Identyfikator"], "Operacja", "1", address)
            self.send(0, headers["Identyfikator"], "Odpowiedz", "e2", address)

    def generate_id(self):
        """
        generuje losowe id dla klienta
        :return: id klienta - wartość całkowita
        """
        id = random.randint (self.id_seed, self.id_seed + 10)
        self.id_seed += 10
        return id

    def settime(self):
        """
        Oblicza i ustawia czas rozgrywki w oparciu o id dwóch pierwszych klientów
        """
        i = 0
        id1 = 0
        id2 = 0
        for id in self.client_list.keys ():
            if i == 0:
                id1 = id
                i += 1
            elif i == 1:
                id2 = id
                i += 1
            else:
                break
        self.gametime = ((abs (int (id1) - int (id2)) * 74) % 90 + 25)

    def main_program(self):
        """
        rozgrywka - generuje losową liczbe z przedziału 0-99,
        odbiera i przetwarza odpowiedzi od klientów,
        informuje o końcu gry z powodu odgadnięcia liczby lub
        końca czasu
        """
        self.number = random.randint (0, 100)
        self.isguessed = False
        self.threadstopper = False
        print ("List of players", self.client_list)
        print ("Wygenerowany numer:", self.number)
        print ("Gametime:", self.gametime)
        t1 = threading.Thread (target=self.counttime, args=[0])
        t1.start ()
        winner = 0
        t2 = threading.Thread (target=self.sendtime)
        t2.start ()
        for clientid, clientaddress in self.client_list.items():
            self.send(2, clientid, "Operacja", "14", clientaddress)
            self.send(1, clientid, "Odpowiedz", "ok", clientaddress)
            self.send(0, clientid, "VAL", str(self.gametime), clientaddress)
        while not self.isguessed and len (self.client_list) > 0 and not self.err:
            data, address = self.recieve ()
            headers = self.parse_headers (data)
            while int (headers["NSekwencyjny"]) > 0:
                data, address1 = self.recieve ()
                headers = self.parse_headers (data)
            if headers["Operacja"] == "timeout":
                self.threadstopper = True
                break
            elif headers["Operacja"] == "1":
                self.send(1, headers["Identyfikator"], "Operacja", "1", address)
                self.send(0, headers["Identyfikator"], "Odpowiedz", "3", address)
            elif headers["Operacja"] == "16":
                temp = collections.OrderedDict ()
                for id, addr in self.client_list.items ():
                    if str (id) != headers["ID"]:
                        temp[id] = addr
                self.client_list = temp
                self.send (1, headers["Identyfikator"], "Operacja", "16", address)
                self.send (0, headers["Identyfikator"], "Odpowiedz", "17", address)
                print ("clients:", self.client_list)
            elif int(headers["Identyfikator"]) in self.client_list.keys():
                print("Rozpoznano")
                winner = self.execute_operation (headers, address, self.number)
            else:
                print("ERROR")
                self.send(1, headers["Identyfikator"], "Operacja", "18", address)
                self.send(0, headers["Identyfikator"], "Odpowiedz", "e3", address)
        if self.isguessed:
            for clientid, clientaddress in self.client_list.items ():
                if clientid != winner:
                    self.send(1, clientid, "Operacja", "7", clientaddress)
                    self.send(0, clientid, "Odpowiedz", "9", clientaddress)
                self.send(1, clientid, "Operacja", "16", clientaddress)
                self.send(0, clientid, "Odpowiedz", "17", clientaddress)
        else:
            for clientid, clientaddress in self.client_list.items ():
                self.send(1, clientid, "Operacja", "7", clientaddress)
                self.send(0, clientid, "Odpowiedz", "8", clientaddress)
                self.send(1, clientid, "Operacja", "16", clientaddress)
                self.send(0, clientid, "Odpowiedz", "17", clientaddress)
        self.client_list = collections.OrderedDict()

    def sendtime(self):
        tim = time.time ()
        while not self.isguessed and self.gametime - (time.time () - self.starttime) > 0 and not self.threadstopper:
            if time.time () - tim > 15:
                for clientid, clientaddress in self.client_list.items ():
                    self.send (2, clientid, "Operacja", "14", clientaddress)
                    self.send(1, clientid, "Odpowiedz", "ok", clientaddress)
                    self.send (0, clientid, "VAL", clientaddress=clientaddress,
                               val=str (int (self.gametime - (time.time () - self.starttime))))
                tim = time.time ()

    def execute_operation(self, headers, address, number):
        """
        :param headers: przetworzona wiadomość od klienta
        :param address: adres klienta
        :param number: nr do odgadnięcia
        sprawdza czy podana przez klienta liczba jest równa tej do odgadnięcia
        i informuje czy trafił/za nisko/za wysoko.
        :return: 0 jeżeli klient nie zgadł, id klienta jeżeli trafił
        """
        if headers["Operacja"] == '10':
            temp = ""
            i = 0
            try:
                check = int(headers["VAL"])
            except ValueError:
                self.send (1, headers["Identyfikator"], "Operacja", "10", address)
                self.send (0, headers["Identyfikator"], "Odpowiedz", "e1", address)
                return 0
            if int(headers["VAL"]) == number:
                temp = "13"
                self.isguessed = True
            elif int(headers["VAL"]) > number:
                temp = "11"
            elif int(headers["VAL"]) < number:
                temp = "12"
            self.send(1, headers["Identyfikator"], "Operacja", "10", address)
            self.send(0, headers["Identyfikator"], "Odpowiedz", temp, address)
            if self.isguessed:
                return int(headers["Identyfikator"])
            else:
                return 0
        else:
            self.send(1, headers["Identyfikator"], "Operacja", "error", address)
            self.send(0, headers["Identyfikator"], "Odpowiedz", "e2", address)
            return 0


if __name__ == "__main__":
    """
    Nieskończona pętla tworząca obiekt gry, i wywołująca po kolei
    funkcje zbierania graczy, ustawiania czasu i gry głównej.
    """
    while True:
        try:
            GON = GameOfNumbers()
            start = False
            """
            Za pomocą poniższej zmiennej można regulować maksymalną ilość graczy
            """
            amount_of_players = 2
            while not start:
                start = GON.collect_players (amount_of_players)
                if amount_of_players > 2 and not start:
                    """
                    Jeżeli nie udało się zacząć gry i oczekiwana liczba graczy
                    jest większa od 2, to zmniejsz liczbę graczy o 1.
                    """
                    amount_of_players -= 1
                    print("not enough")
            GON.starttime = time.time()
            GON.settime()
            GON.main_program()
            GON.threadstopper = True
            del GON
        except BaseException:
            GON.threadstopper = True
            for clientid, clientaddress in GON.client_list.items():
                GON.send (1, clientid, "Operacja", "error", clientaddress)
                GON.send (0, clientid, "Odpowiedz", "e3", clientaddress)
                GON.send (2, clientid, "Operacja", "16", clientaddress)
                GON.send (1, clientid, "Odpowiedz", "disconnected", clientaddress)
                GON.send (0, clientid, "VAL", "17", clientaddress)
            del GON

