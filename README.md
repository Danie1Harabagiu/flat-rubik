# Flat Rubik

Simulator Rubik 3×3×3 cu afișare exclusiv circulară 2D, Python 3.12 și
Pygame 2.6.1. Modelul conține 26 de cubulețe fizice (6 centre, 12 muchii,
8 colțuri), cu identități persistente și 54 de suprafețe colorate.

## Instalare și pornire

```powershell
python -m pip install -r requirements.txt
python main.py
```

## Alegerea modului: Rubik 90° sau Puzzle 45°

Aplicația pornește implicit în **Rubik 90°**, cu mecanica cubului fizic.
Butonul **Mod: Rubik 90° | schimbă** comută la **Puzzle 45°** și invers.
Cele două jocuri au stări separate; schimbarea modului nu resetează pozițiile.

În **Puzzle 45°**, fiecare clic deplasează cele opt piese ale feței cu o
poziție în ciclul de opt locuri. Clic dreapta inversează mutarea. Poți roti
imediat oricare altă față, fără aliniere suplimentară. Muchiile și colțurile
pot schimba locurile între ele: fiecare piesă își păstrează identitatea,
cele două sau trei culori și ordinea lor, iar forma se adaptează poziției.
La rotațiile laterale, orientarea partiției colorate avansează tot cu 45°.
Centrele rămân fixe. Opt pași pe aceeași față refac pozițiile și orientările.
Acesta este un puzzle nou, cu reguli diferite de cubul Rubik fizic.

Tastele fețelor folosesc pasul modului activ. **Ctrl + față** face doi pași;
în modul de 45°, **Ctrl + Shift + față** face doi pași în sens invers.
Amestecarea și resetarea acționează asupra modului activ. Editorul **Culori**
lucrează cu modul Rubik; în modul nou, butonul **Rubik: culori** te duce acolo.

## Salvarea automată a pozițiilor

După fiecare mutare terminată, aplicația salvează automat ambele jocuri în
`puzzle_session.json`, separat de configurația manuală din `cube_colors.json`.
La următoarea deschidere restaurează pozițiile și vitezele, pornind în Rubik.
Pentru a continua varianta de 45°, apasă butonul de mod.
O animație în curs și mutările încă în coadă nu sunt salvate: se păstrează
ultima poziție completă. Fișierul sesiunii este local și ignorat de Git.

## Comenzi

| Tastă | Acțiune |
| --- | --- |
| Clic stânga pe un centru | Rotație de 90° în sens orar, privind fața din exterior |
| Clic dreapta pe un centru | Aceeași față în sens invers |
| R, L, U, D, F, B | Rotație de 90° în sens orar, privind fața din exterior |
| Shift + față | Rotație inversă |
| Ctrl + față | Rotație dublă |
| 2, apoi față | Rotație dublă; apăsarea repetată a lui 2 dezactivează modul |
| Spațiu | Adaugă 25 de mutări de amestecare în coadă |
| Home | Resetare imediată; golește coada și animația |
| Esc | Ieșire |
| P | Pauză / continuare |
| + / - | Mărește / micșorează durata rotației |
| E | Deschide editorul „Culori”; în editor renunță la modificări |

F = roșu, B = portocaliu, U = galben, R = verde, D = alb, L = albastru.
Clicurile funcționează pe cercul roșu, inelul portocaliu și cele patru
centre laterale de o singură culoare. Centrele sunt evidențiate prin insigne
contrastante cu literele F, B, U, R, D, L. Clicurile pe piesele mobile sau în
spațiile libere sunt ignorate. Mutările se adaugă în coada de animații,
inclusiv când o rotație este deja în curs. Detectarea se adaptează la
redimensionarea ferestrei.
Durata inițială este de 1 secundă pe mutare, inclusiv pentru cele duble.
Glisorul „Durata rotației” permite reglarea între 0,2 și 3 secunde;
spre dreapta animația devine mai lentă. Reglarea în timpul unei mutări
păstrează progresul curent, fără salt. Butonul „Pauză” oprește temporar
animația pentru a inspecta piesele; „Continuă” reia din același punct.
Interfața rămâne activă pe durata animației; ținta este 60 FPS.
Fereastra este redimensionabilă.

## Introducerea culorilor cubului fizic

Apasă **Culori** sau **E** și dă clic pe suprafața pe care vrei s-o colorezi.
Fiecare clic trece la culoarea următoare, fără selecție din paletă.
Întreaga suprafață își schimbă culoarea. Copiază
astfel configurația cubului fizic. Orientează cubul fizic cu roșu în față,
portocaliu în spate, galben sus, alb jos, verde dreapta și albastru stânga.
Cele șase centre rămân fixe; cele 48 de suprafețe mobile pot fi editate.

- Clic stânga: următoarea culoare (roșu → portocaliu → galben → verde → albastru → alb → roșu).
- Clic dreapta: culoarea precedentă, în sens invers.
- **Anulează** sau **Ctrl+Z**: anulează ultima modificare.
- **Rezolvat** sau **Delete**: pregătește configurația rezolvată în editor.
- **Random valid**: pregătește o configurație aleatorie posibilă.
- **Aplică** sau **Enter**: verifică și instalează configurația pentru rotații.
- **Renunță**, **E** sau **Esc**: închide editorul fără schimbarea cubului activ.

Contorul arată numărul suprafețelor din fiecare culoare; trebuie să existe
câte 9. Aplicarea verifică și combinațiile muchiilor/colțurilor, piesele
duplicate, orientările, colțurile în oglindă și paritatea permutărilor.
O stare imposibilă afișează motivul și rămâne deschisă pentru corectare.
La aplicare se reconstruiesc identitățile și orientările celor 26 de cubulețe,
iar rotațiile și animațiile folosesc efectiv configurația introdusă.

În editor, animația și coada sunt suspendate. Aplicarea înlocuiește starea
și golește mutările vechi; renunțarea permite continuarea stării anterioare.
Lucrul în curs și ultima configurație aplicată se salvează separat în
`cube_colors.json`, ignorat de Git. La pornire se restaurează ultima stare
aplicată, iar editorul permite reluarea culorilor neterminate. Rotațiile
efectuate ulterior nu rescriu configurația manuală salvată.

[Editorul culorilor](assets/colors-preview.png)

## Amestecare în configurații posibile

Butonul **Amestecă** sau **Spațiu** adaugă 25 de mutări Rubik legale în coadă.
Configurațiile provin exclusiv din rotații ale cubului real; nu se generează
culori independente pe suprafețe. Astfel, pornind de la cubul rezolvat,
amestecarea păstrează configurații fizic posibile. În editor, **Random valid**
pregătește o asemenea configurație, pe care o poți instala prin **Aplică**.

## Interfață și urmărirea mutărilor

Panoul lateral oferă șase butoane cu numele și culorile fețelor, controlul
vitezei, pauză, afișarea traseelor și resetare. Clic stânga/dreapta pe butoane
are același efect ca pe centre. În ferestre mai mici panoul se mută sub desen.

Zonele fețelor au fundaluri discret colorate și delimitări fixe, independente
de culorile pieselor amestecate. Zona selectată cu mouse-ul sau rotită în acel
moment este evidențiată împreună cu insigna și butonul corespunzător.
La trecerea mouse-ului peste un centru sau buton, un halou alb evidențiază
toate cele opt cubulețe pe care le va antrena stratul, cu toate suprafețele
lor colorate, precum și centrul selectat. Haloul rămâne vizibil la rotire.
Culorile originale rămân complet opace și nemodificate.
Traseele punctate opționale au cerc la plecare și săgeată la sosire, câte un
traseu pentru fiecare cubuleț fizic mobil, calculat din transformarea stratului.
Implicit sunt oprite. Nu se desenează copii sau contururi-fantomă ale pieselor
destinație, pentru a evita impresia de suprapunere.

[Captură a interfeței](assets/interface-preview.png) ·
[Exemplu în timpul rotației](assets/animation-preview.png) ·
[Demonstrație animată a stratului](assets/layer-rotation-preview.gif)

## Geometrie după fotografiile de referință

Proiecția reproduce structura celor două imagini furnizate: opt direcții la
intervale de 45°, cu piese separate prin spații pe fundal mov. Imaginea fără marcaje
stabilește contururile, iar imaginea cu marcaje arată delimitarea fețelor.
Marcajele colorate trasate de mână nu fac parte din contururile pieselor.

Cercul roșu central are raza 32, micșorată pentru a oferi mai mult spațiu
pieselor interioare. Inelul portocaliu ocupă razele 300–330, mai îngust
pentru a reduce greutatea vizuală a exteriorului.
Centrele laterale ocupă pozițiile cardinale ale rândului mijlociu,
între razele 133–202, cu deschidere de 36°. Galbenul este sus, verdele în
dreapta, albul jos și albastrul în stânga, conform fotografiei.

Fiecare cubuleț mobil ocupă o singură regiune compusă: două culori pentru
muchii, trei pentru colțuri. La interior, roșul ocupă partea apropiată de
centru; la exterior, portocaliul ocupă partea apropiată de inel. La colțuri
și la muchiile diagonale, culorile laterale împart lățimea regiunii. Cele
48 de suprafețe mobile aparțin celor 20 de cubulețe mobile.

La dimensiunea 800×800, rândurile mobile ocupă razele 38–126, 133–202 și
209–292. Rândul interior este cu aproximativ 28% mai lat radial decât în
varianta anterioară, iar cel exterior cu aproximativ 26% mai îngust.
Spațiile radiale au fost reduse la 6–8 pixeli, iar cele unghiulare
la 9°, conform preferinței utilizatorului pentru piese mai apropiate.
Separarea roșu/lateral este la raza 82, iar separarea
lateral/portocaliu la 246. **Proporțiile pornesc de la fotografii și sunt
ajustate după preferințele utilizatorului, nu măsurători exacte.**
Razele sunt definite într-un singur loc în `geometry.py` și folosite atât
de desenul static, cât și de animație, delimitări și detectarea clicurilor.
`assets/reference-layout-preview.png`
este captura generată a implementării curente.

Animația aplică o singură transformare comună întregului strat. Fețele F/B
rotesc rigid rândurile interioare/exterioare. Fețele laterale folosesc un
inel pătrat într-un reper comun, transformat înapoi în desenul circular.
Transformarea este injectivă: celulele cubulețelor rămân distincte și
ocolesc centrul fix. Cele două sau trei culori ale unui cubuleț împart aceeași
regiune și aceleași margini; nu mai au traiectorii independente. Delimitările
interioare se adaptează împreună la forma destinație. Nu există contracție
suplimentară, estompare sau copii ale pieselor. Pornirea și oprirea sunt line.

Geometria circulară impune deformarea coordonată a stratului lateral; aceasta
este o animație 2D care păstrează legăturile, nu o proiecție perspectivă 3D.
Testele verifică absența suprapunerilor interioare în 162 de cadre pentru
toate cele 18 mutări, inclusiv pe un cub amestecat, plus centrele fixe,
marginile comune și apropierea continuă de stările inițială/finală.
Contururile vecine pot împărți pixeli de margine din cauza rasterizării.
Centrele sunt desenate deasupra pieselor și rămân fixe.
Ferestrele foarte mici reduc lizibilitatea contururilor și a textului.

## Structură

- `cube.py`: coordonate 3D întregi, identități și orientări prin normalele
  suprafețelor; rotații exacte, fără dependență de Pygame.
- `projection.py`: corespondență între suprafețele modelului și pozițiile 2D;
  nu creează copii logice ale cubulețelor.
- `geometry.py`: centre, arce, eșantionare și interpolare.
- `animation.py`: coadă neblocantă și aplicarea stării la finalul fiecărei mutări.
- `layer_motion.py`: rotație comună a stratului, celule distincte și culori unite.
- `renderer.py`: culori, contururi și centre fixe.
- `app.py`: evenimente, tastatură, redimensionare și buclă la 60 FPS.
- `ui.py`: panou adaptabil, butoane și glisor pentru durata rotației.
- `editor.py`: selectarea și colorarea suprafețelor, anulare și salvare locală.
- `state.py`: reconstruirea cubulețelor și validarea unei configurații fizic posibile.

## Teste

[Verificarea față de cubul fizic](docs/physical-model-audit.md) include
comparația cu o referință independentă și un protocol practic de urmărit
alături de cubul real. Testele dedicate verifică toate cele 18 mutări,
324 de perechi, 5.000 de pași și 1.000 de stări valide generate separat.

```powershell
python -m unittest discover -s tests -v
```

Testele verifică inventarul, identitățile și pozițiile unice, centrele fixe,
culorile, rotațiile și inversele, exemple independente de orientare,
250 de mutări urmate de inverse, cele 54 de suprafețe proiectate,
redimensionarea, coada, controalele mouse, pauza, schimbarea vitezei fără salt
și păstrarea ariei conturului la schimbarea orientării. Testul Pygame folosește
driverul SDL `dummy` și verifică desenarea cercului roșu, apoi pornește
bucla aplicației pentru trei cadre, fără a deschide o fereastră vizibilă.
