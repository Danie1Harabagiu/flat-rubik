# Verificarea Flat Rubik față de cubul fizic

Rezultat: modelul logic și stările de la sfârșitul mutărilor corespund unui
cub Rubik 3×3×3 în verificările efectuate. Nu au fost găsite abateri ale
permutărilor sau orientărilor. Animația intermediară este o transformare 2D
adaptată desenului circular, nu o proiecție geometrică exactă a rotației 3D.

## Referință independentă

Testele din `tests/test_physical_model.py` folosesc permutări fixe ale celor
54 de suprafețe, după [definițiile publicate de Herbert Kociemba](https://kociemba.org/math/CubeDefs.htm).
Ele nu apelează funcția `rotate` sau validarea aplicației pentru a genera
rezultatele așteptate. Fiecare suprafață are o etichetă unică U1…B9, astfel
încât comparația urmărește identitatea exactă, nu doar culorile repetitive.

Numerotarea fețelor și gruparea muchiilor/colțurilor urmează
[convenția facelet](https://kociemba.org/math/faceletlevel.htm) și
[convenția cubie](https://kociemba.org/math/cubielevel.htm).

## Verificări efectuate

| Verificare | Rezultat |
| --- | --- |
| 26 de cubulețe: 6 centre, 12 muchii, 8 colțuri | Corect |
| 54 de suprafețe, câte 9 de fiecare culoare | Corect |
| Toate cele 18 mutări: 6 fețe × simplă/inversă/dublă | Coincid cu referința |
| Toate cele 324 de perechi de mutări | Coincid cu referința |
| 5.000 de pași aleatorii consecutivi, verificare după fiecare pas | Toate cele 54 de identități coincid |
| 1.000 de stări valide generate independent prin permutări și orientări | Importate cu identități și orientări corecte |
| Fiecare rotație de față mută 4 muchii și 4 colțuri | Corect |
| Centrele rămân fixe; 20 de suprafețe își schimbă poziția la un sfert de tură | Corect |
| Gruparea suprafețelor în desenul circular | Păstrează cubulețele fizice |
| Patru sferturi de tură și mutare urmată de inversă | Revin la starea inițială |
| Editor: număr de culori, piese duplicate, oglindire, orientare, paritate | Verificate |
| Animație: suprafețe unite, destinații corecte, interioare fără suprapunere în cadrele testate | Verificate |

Validarea orientărilor și parității corespunde verificărilor din
[implementarea de referință](https://github.com/hkociemba/RubiksCube-TwophaseSolver/blob/master/cubie.py).
Centrele sunt fixe, suma răsucirilor colțurilor este zero modulo 3,
suma răsturnărilor muchiilor este zero modulo 2, iar permutările muchiilor
și colțurilor au aceeași paritate.

```powershell
python -m unittest discover -s tests -p test_physical_model.py -v
python -m unittest discover -s tests -v
```

## Comparație practică, lângă cubul tău

Acesta este un protocol de verificare manuală, nu un experiment fizic deja
efectuat. Verificarea software nu confirmă singură că ai copiat corect toate
culorile de pe un anumit cub fizic.

1. Pornește din starea rezolvată în ambele reprezentări. În aplicație folosește
   **Home**. Pentru o configurație deja copiată și aplicată corect, poți porni
   și cu ambele cuburi în acea configurație identică.
2. Orientează cubul fizic cu roșu în față, galben sus, verde la dreapta,
   portocaliu în spate, alb jos și albastru la stânga. Pe parcurs păstrează
   această orientare a întregului cub.
3. Execută **R**: rotește fața verde în sens orar privind direct acea față
   din exterior. În aplicație apasă **R** sau clic stânga pe centrul verde.
4. Dacă ai pornit rezolvat, colțul roșu–galben–verde ajunge din față–sus–dreapta
   în spate–sus–dreapta. Roșul ajunge sus, galbenul în spate, verdele rămâne
   pe fața dreaptă. În desenul circular, piesa ajunge pe direcția sus–dreapta
   în rândul exterior.
5. Execută **R'** pe ambele: sens invers pe cubul fizic și clic dreapta pe
   centrul verde în aplicație. Starea de pornire trebuie restabilită.
6. Compară apoi după fiecare pas din **R U R' U'**. Pentru inversă la
   tastatură folosește **Shift + litera feței**. Compară identitatea
   cubulețului și fața pe care se află fiecare culoare, nu forma sa 2D.

## Ce păstrează și ce schimbă reprezentarea circulară

La finalul fiecărei mutări, fiecare cubuleț, poziție și culoare are
corespondentul fizic corect. Nu există piese suplimentare sau copii
independente ale suprafețelor aceluiași cubuleț.

În timpul animației, stratul lateral se deformează coordonat pentru a rămâne
în domeniul circular 2D și a ocoli centrele. Formele, distanțele și
rigiditatea geometrică nu reproduc literalmente un cub din spațiu.
Această limitare vizuală nu schimbă rezultatul logic al mutării.

Concluzia se aplică schemei de culori a aplicației și cubului 3×3×3 cu centre
de o singură culoare, fără a urmări orientarea desenelor de pe centre.
