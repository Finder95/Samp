# Samp

## AutoRP – automatyzacja tworzenia gamemodu RP

Repozytorium zawiera narzędzie **AutoRP**, które potrafi wygenerować kompletny pakiet
gamemodu RolePlay dla SA-MP – od pliku Pawn, przez konfigurację serwera, aż po szkielety
automatycznych testów z wykorzystaniem botów sterujących klientem GTA:SA.

Konfiguracja (w formacie JSON) opisuje cały świat gry: frakcje, pojazdy, zadania, pickupy,
nieruchomości z punktami wejścia/wyjścia, biznesy, questy, receptury rzemieślnicze,
osiągnięcia, system umiejętności z treningami, kontrolę terytoriów, cykle pogody oraz
NPC-ów z dialogami i harmonogramami zdarzeń. AutoRP tłumaczy je na gotowe struktury Pawn,
timery i komendy zarządzające gospodarką RP.

### Najważniejsze funkcje
- elastyczna konfiguracja w JSON-ie opisująca frakcje, punkty odrodzeń, pojazdy,
  komendy i parametry świata;
- generator Pawn tworzący gotowy do kompilacji gamemode z obsługą frakcji, komend,
  pakietów startowych, ekonomii, ekwipunku oraz logów inicjalizacyjnych;
- automatyczne przygotowanie nieruchomości z pickupami i komendami zakupu oraz NPC-ów
  z konfigurowalnymi dialogami i kontrolą dostępu frakcyjnego;
- generowanie biznesów z pickupami informacyjnymi, komendami zakupów i kontrolą pracy
  frakcji lub stanowiska;
- system questów narracyjnych i osiągnięć wraz z komendami pomocniczymi oraz nagrodami;
- rozbudowany system umiejętności z progami XP, komendami podglądu oraz treningami
  przyznającymi doświadczenie z cooldownami;
- dynamiczna kontrola terytoriów wraz z timerami przejęcia, nagrodami i broadcastami dla
  całego serwera;
- definiowanie cyklicznych eventów (np. premie służbowe, loterie) wykonywanych poprzez
  timery wraz z broadcastami, komendami RCON oraz nagrodami pieniężnymi;
- wsparcie dla recept rzemieślniczych i automatycznych komunikatów o brakujących
  mechanikach serwerowych, aby łatwo rozszerzyć bazowy kod Pawn;
- dynamiczny cykl pogody z timerem rotującym warunki w grze oraz broadcastami dla graczy;
- przygotowanie kompletnej paczki serwerowej (`server.cfg`, metadane) jednym poleceniem;
- opcjonalna kompilacja do pliku AMX (wymagany `pawncc` w systemie);
- orkiestrator testów zdolny do uruchamiania lokalnego serwera SA-MP i sterowania botami;
- generowanie scenariuszy botów na podstawie konfiguracji (plików JSON) gotowych do
  wykorzystania przez narzędzia QA.

### Szybki start
1. Przygotuj konfigurację (przykład w `configs/sample_config.json`).
2. Wygeneruj paczkę serwerową:
   ```bash
   python -m tools.autorp.cli configs/sample_config.json --package-dir build/server
   ```
   W katalogu `build/server` znajdziesz m.in. `gamemodes/AutoRP.pwn`, `server.cfg` i plik
   `autorppackage.json` z metadanymi.
3. (Opcjonalnie) skompiluj gamemode od razu po wygenerowaniu:
   ```bash
   python -m tools.autorp.cli configs/sample_config.json --package-dir build/server --compile
   ```
   Domyślnie narzędzie doda katalog `inc/` jako ścieżkę include dla kompilatora Pawn.

4. (Opcjonalnie) wyeksportuj scenariusze botów z konfiguracji do katalogu:
   ```bash
   python -m tools.autorp.cli configs/sample_config.json --bot-scripts-dir build/bots
   ```
   Każdy scenariusz opisany w sekcji `bot_scenarios` konfiguracji zostanie zapisany jako osobny
   plik JSON zawierający sekwencję kroków do odpalenia w orchestratorze testów.

### Automatyczne testy botów
Moduł `tools.autorp.tester` udostępnia klasę `TestOrchestrator`, która potrafi uruchomić
lokalny serwer SA-MP (klasa `SampServerController`), zapisać scenariusze botów na dysk i
wykonać je na zadanych klientach (implementujących interfejs `BotClient`). Dzięki temu
można łatwo zintegrować scenariusze e2e z pipeline CI/CD.

### Testy
```bash
pytest
```
