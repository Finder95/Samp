# Samp

## AutoRP – automatyzacja tworzenia gamemodu RP

Repozytorium zawiera narzędzie **AutoRP**, które potrafi wygenerować kompletny pakiet
gamemodu RolePlay dla SA-MP – od pliku Pawn, przez konfigurację serwera, aż po szkielety
automatycznych testów z wykorzystaniem botów sterujących klientem GTA:SA.

Konfiguracja (w formacie JSON) opisuje cały świat gry: frakcje, pojazdy, zadania, pickupy,
nieruchomości z punktami wejścia/wyjścia, biznesy, questy, receptury rzemieślnicze,
osiągnięcia, system umiejętności z treningami, kontrolę terytoriów, system prawa z kodeksem,
cykle pogody, trasy patroli, wieloetapowe heisty oraz NPC-ów z dialogami i harmonogramami
zdarzeń. AutoRP tłumaczy je na gotowe struktury Pawn, timery i komendy zarządzające
gospodarką RP.

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
- kodeks wykroczeń oraz komendy /kodeks, /wanted i /zakoncz_patrol wspierające monitorowanie
  reputacji graczy i egzekwowanie prawa podczas symulacji serwerowych;
- generowanie tras patroli frakcyjnych z komendami startu/stopu, teleportami i odliczaniem
  punktów kontrolnych;
- wieloetapowe heisty treningowe z cooldownami, nagrodami pieniężnymi, komunikatami oraz
  automatycznym naliczaniem poziomu poszukiwania;
- definiowanie cyklicznych eventów (np. premie służbowe, loterie) wykonywanych poprzez
  timery wraz z broadcastami, komendami RCON oraz nagrodami pieniężnymi;
- wsparcie dla recept rzemieślniczych i automatycznych komunikatów o brakujących
  mechanikach serwerowych, aby łatwo rozszerzyć bazowy kod Pawn;
- dynamiczny cykl pogody z timerem rotującym warunki w grze oraz broadcastami dla graczy;
- przygotowanie kompletnej paczki serwerowej (`server.cfg`, metadane) jednym poleceniem;
- opcjonalna kompilacja do pliku AMX (wymagany `pawncc` w systemie);
- orkiestrator testów zdolny do uruchamiania lokalnego serwera SA-MP i sterowania botami;
- generowanie scenariuszy botów na podstawie konfiguracji (plików JSON) gotowych do
  wykorzystania przez narzędzia QA;
- biblioteka klientów botów w `tools.autorp.bots` z obsługą plikowych kolejek komend,
  tłumaczeniem akcji scenariuszy i integracją z klientem SA-MP uruchamianym przez Wine.

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

5. (Opcjonalnie) uruchom automatyczne testy botów bezpośrednio po wygenerowaniu paczki:
   ```bash
   python -m tools.autorp.cli \
       configs/sample_config.json \
       --package-dir build/server \
       --run-bot-tests \
       --gta-dir /sciezka/do/instalacji/gta \
       --bot-command-file build/server/bot_commands.txt
   ```
   Powyższe polecenie uruchomi lokalny serwer SA-MP, wystartuje klienta przez Wine i wyśle
   kroki scenariusza na podstawie konfiguracji. Użyj przełącznika `--bot-dry-run`, aby
   zamiast prawdziwego klienta zapisywać komendy do pliku i symulować odtwarzanie.

### Automatyczne testy botów
Moduł `tools.autorp.tester` udostępnia klasę `TestOrchestrator`, która potrafi uruchomić
lokalny serwer SA-MP (klasa `SampServerController`), zapisać scenariusze botów na dysk i
wykonać je na zdefiniowanych klientach (implementujących interfejs `BotClient`). Orkiestrator
obsługuje wiele klientów jednocześnie, śledzi oczekiwane wpisy w `server_log.txt` (przez
`ServerLogMonitor`) oraz w logach samych klientów (przez `ClientLogMonitor`) i umożliwia
budowanie planów testowych (`BotRunContext`) z powtórzeniami, opóźnieniami oraz asercjami na
logi serwera i logi klienckie.

Konfiguracja JSON może zawierać blok `bot_automation`, w którym definiujemy listę klientów
(`clients`) oraz przebiegów (`runs`). Każdy przebieg wskazuje scenariusz z sekcji
`bot_scenarios`, listę klientów do uruchomienia, oczekiwane frazy w logach serwera oraz
liczbę iteracji i odstępów między nimi. Dodatkowo można aktywować zbieranie logu serwera
(`collect_server_log`, `server_log_export`) i eksportować konkretne logi klienckie
(`export_client_logs`) – każdy wpis pozwala wskazać klienta, nazwę logu, katalog docelowy
oraz czy zapisać cały plik czy jedynie przyrost z danego przebiegu. Przykładowa konfiguracja
znajduje się w `configs/sample_config.json`.

Scenariusze botów mogą korzystać z makr (`bot_macros` oraz lokalnych `macros` w obrębie
`bot_scenarios`), które pozwalają wielokrotnie wykorzystywać zestawy kroków z parametrami i
podstawianiem zmiennych `{{variable}}` w treści akcji. Wartości zmiennych pochodzą z sekcji
`bot_variables`, pól `variables` scenariuszy oraz – opcjonalnie – z parametru CLI
`--bot-var KEY=VALUE`, dzięki czemu zestawy testów można łatwo konfigurować bez edycji pliku
JSON. Makra są rozwijane przed generowaniem skryptów, więc gotowe scenariusze zachowują pełną
kompatybilność z istniejącym translaterem akcji.

Oczekiwania logów serwera mogą być teraz bogatsze niż pojedyncze ciągi znaków. W definicjach
`expect_server_logs` dopuszczalne jest wskazanie liczby wymaganych wystąpień (`occurrences`),
czasu oczekiwania (`timeout`), sposobu dopasowania (`match_type` ustawione na `substring` lub
`regex`) oraz czułości na wielkość liter (`case_sensitive`). `ServerLogMonitor` raportuje liczbę
znalezionych dopasowań, co umożliwia precyzyjne walidowanie dynamicznych wydarzeń po stronie
serwera i zapisywanie fragmentów logu w artefaktach przebiegu.

Moduł `tools.autorp.bots` zawiera gotowe implementacje klientów:

- `WineSampClient` – uruchamia prawdziwego klienta SA-MP przez Wine (z obsługą dry-run,
  czyszczenia pliku komend, konfigurowanego opóźnienia po połączeniu, opcjonalnego fokusu
  okna przez `WineWindowInteractor` oraz zrzutów ekranu po zakończeniu przebiegu);
- `DummyBotClient` – lekka implementacja do testów jednostkowych lub środowisk CI, która
  zapisuje sekwencje komend bez uruchamiania GTA:SA;
- `FileCommandTransport`, `BufferedCommandTransport` oraz `ScriptRunner` – pozwalają tworzyć
  własne integracje z makrami lub CLEO, tłumacząc akcje scenariuszy (`wait`, `chat`,
  `teleport`, `keypress`, `macro`, `wait_for`, `focus_window`, `type_text`, `mouse_move`,
  `mouse_click`, `mouse_scroll`, `mouse_drag`, `key_sequence`, `key_combo`, `screenshot`,
  `config`, komendy tekstowe)
  na rzeczywiste instrukcje, a także raportując przechwycone logi klientów.

`WineWindowInteractor` zapewnia owijarkę na `xdotool`, co pozwala na aktywację okna Wine,
symulowanie wpisywania tekstu, pojedynczych zdarzeń klawiszowych (`key`, `key_event`) oraz
ruchów i przewijania myszy w trakcie wykonywania scenariuszy. Klient może automatycznie
zrealizować sekwencje przygotowawcze (`setup_actions`) i porządkowe (`teardown_actions`)
jeszcze przed wykonaniem właściwego scenariusza, a każda akcja `screenshot` rejestruje plik do
raportu z przebiegu. Nowe ustawienia pozwalają także zebrać fragmenty logów czatu lub innych
plików dzięki `ClientLogMonitor` oraz zapisać je w katalogach artefaktów.

Każdy przebieg scenariusza zwraca `PlaybackLog` z wysłanymi akcjami, znacznikami czasu oraz
łączną długością trwania odtworzenia. Rezultat `TestRunResult` zawiera listę klientów, którzy
ukończyli test, status dopasowania oczekiwań z logów serwera i logów klienckich, dane o próbie
i iteracji, a także czas trwania przebiegu. Jeśli włączono rejestrowanie, wynik zawiera również
ścieżki do zapisanych logów odtworzenia, zebrane zrzuty ekranu oraz spójne podsumowanie
niepowodzeń (`RunFailure`) pogrupowanych według kategorii (klient, log serwera, log klienta).
Orkiestrator wspiera wielokrotne próby (`max_retries`), okresy wyciszenia przed kolejną próbą
(`grace_period`), tagowanie przebiegów oraz przerwanie całej suity po pierwszym błędzie
(`fail_fast`). Dodatkowo każdy przebieg można uzupełnić o własne asercje i metryki – sekcja
`assertions` w definicji `bot_automation.runs` pozwala kontrolować łączny czas trwania
(`total_duration`), czas i liczbę komend pojedynczych klientów (`client_duration`,
`command_count`), wymagania dotyczące logów (`require_log`, `log_presence`) oraz liczbę
zebranych zrzutów ekranu (`screenshot_count`). Parametry `min`, `max`, `equals`, `expected`,
`message` i `description` pomagają precyzyjnie opisać oczekiwania, a wynikowe raporty CLI oraz
plik JSON zawierają informacje o spełnionych i niespełnionych asercjach.

Konfiguracja `bot_automation` może teraz oznaczać przebiegi tagami (`tags`), określać liczbę
ponowień (`retries`), przerwy między próbami (`grace_period`) oraz włączać/wyłączać pojedyncze
scenariusze (`enabled`).

Podsumowania suity, scenariuszy, klientów i tagów obejmują także szczegółową analitykę akcji
wykonanych przez boty. CLI i raport JSON prezentują łączną liczbę akcji, rozbicie według typów,
liczbę wywołań screenshotów, faktycznie zapisane pliki oraz skumulowany czas oczekiwania na
akcje `wait`. Dzięki temu łatwo ocenić, które scenariusze lub klienci generują najwięcej
interakcji, gdzie pojawiają się długie pauzy oraz jakie makra wizualne rejestrowały materiał
debugowy.

CLI udostępnia dodatkowe przełączniki wspierające pełną automatyzację (`--xdotool-binary`,
`--bot-focus-window`, `--bot-window-title`, `--bot-record-playback-dir`,
`--bot-server-log-dir`, `--bot-client-log-dir`, `--bot-only`, `--bot-skip`,
`--bot-retries`, `--bot-grace-period`, `--bot-fail-fast`, `--bot-var`,
`--bot-report-json`), które można łączyć z definicjami klientów z konfiguracji (`logs`,
`chatlog`, `setup_actions`, `teardown_actions`, `expect_client_logs`,
`record_playback_dir`, `wait_before`, `wait_after`, `collect_server_log`,
`server_log_export`, `export_client_logs`, `tags`, `retries`, `grace_period`,
`fail_fast`, `assertions`). Filtry `--bot-only` oraz `--bot-skip` działają na opisy scenariuszy
(slug/nazwa) oraz przypisane tagi. Parametr `--bot-var` pozwala nadpisać zmienne używane w
makrach i krokach scenariuszy, a `--bot-report-json` zapisuje podsumowanie wszystkich
przebiegów (statusy, niepowodzenia, asercje, ścieżki do artefaktów) do wskazanego pliku JSON.

### Testy
```bash
pytest
```
