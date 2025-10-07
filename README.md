# Samp

## Rozwiazywanie problemu z komunikatem "To rewrite commits in this repository, you must be a collaborator"

Jesli podczas proby wykonania `git push` lub zatwierdzenia zmian w serwisie GitHub pojawia sie powyzszy komunikat, oznacza to, ze uzywane konto lub token dostepowy nie ma prawa zapisu do repozytorium. Poniżej lista kroków, które zazwyczaj rozwiązuja problem:

1. **Zweryfikuj uprawnienia konta**
   - Zaloguj sie w przegladarce na GitHub i przejdz do repozytorium.
   - W zakladce **Settings → Collaborators** upewnij sie, ze Twoje konto widnieje na liscie z prawami `Write` lub `Admin`.

2. **Sprawdz adres zdalny (remote)**
   ```bash
   git remote -v
   ```
   Jezeli adres wskazuje na cudze repozytorium (np. `github.com/inne-konto/projekt.git`), sklonuj wlasny fork albo zmien adres poleceniem:
   ```bash
   git remote set-url origin git@github.com:twoje-konto/projekt.git
   ```

3. **Uzyj poprawnego sposobu uwierzytelnienia**
   - Dla HTTPS wymagany jest **Personal Access Token** zamiast hasla.
   - Dla SSH upewnij sie, ze klucz publiczny znajduje sie na Twoim koncie GitHub i agent SSH jest uruchomiony (`ssh-add -l`).

4. **Zaktualizuj lokalne dane autora**
   ```bash
   git config user.name "Twoje Imie"
   git config user.email "twoj.mail@example.com"
   ```
   Niepoprawne dane autora nie blokują zapisu, ale ich uzupełnienie eliminuje błędy podczas commitów.

5. **Spróbuj ponownie wypchnac zmiany**
   ```bash
   git push origin <twoja-galaz>
   ```
   Jezeli mimo wszystko pojawia sie komunikat o braku uprawnien, sprawdz czy nie probujesz nadpisac historii (`--force`) w repozytorium, do ktorego masz tylko dostep do odczytu.

Po wykonaniu powyzszych krokow problem powinien zniknac. W razie dalszych trudnosci warto usunac lokalny katalog i ponownie sklonowac repozytorium korzystajac z wlasnych danych uwierzytelniajacych.
