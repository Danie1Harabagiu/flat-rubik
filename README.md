# Flat Rubik

Simulator Rubik 3×3×3 cu afișare exclusiv circulară 2D, Python 3.12 și
Pygame 2.6.1. Modelul conține 26 de cubulețe fizice (6 centre, 12 muchii,
8 colțuri), cu identități persistente și 54 de suprafețe colorate.

## Instalare și pornire

```powershell
python -m pip install -r requirements.txt
python main.py
```

## Pe telefon, în browser

Versiunea web rulează același joc prin Pygbag, fără instalare de Python pe
telefon. Linkul privat este
[Flat Rubik](https://flat-rubik-mobile-daniel.harabagiupavel006.chatgpt.site).
Deschide-l autentificat în contul care deține site-ul. Prima încărcare descarcă
motorul Python; următoarele încărcări folosesc cache-ul browserului.

În poziție verticală apar șase butoane colorate mari, fiecare cu două săgeți:
jumătatea stângă rotește invers, jumătatea dreaptă în sens orar. Poți folosi și
săgețile de pe centre. Comutarea 90°/45°, pauza, amestecarea, culorile și
viteza sunt disponibile prin atingere. Poziția se păstrează în browserul și
telefonul folosit; nu se sincronizează cu salvarea de pe calculator.

Pentru construirea versiunii web pe calculator:

```powershell
python -m pip install -r requirements-web.txt
python scripts/build_web.py
python -m http.server 8000 --bind 0.0.0.0 --directory dist
```

Pe telefon, în aceeași rețea Wi-Fi, deschide `http://IP-CALCULATOR:8000`.
Fișierele de publicat sunt în `dist`. Împachetarea include
doar codul jocului, fără salvările personale. Workflow-ul GitHub **Build phone
browser version** verifică jocul și produce arhiva `flat-rubik-web` la push;
publicarea Sites este separată. Șablonul web este adaptat din
[Pygbag 0.9.3](https://github.com/pygame-web/pygbag), sub licență MIT.

## Publicare pe GitHub Pages

În repository-ul `Danie1Harabagiu/flat-rubik`, deschide **Settings → Pages**
și alege **GitHub Actions** la **Build and deployment → Source**.
Trimite modificările pe ramura `main`. Workflow-ul **Build and publish phone
browser version** verifică jocul, construiește versiunea web și o publică.
Poate fi pornit și manual din fila **Actions**, prin **Run workflow**.

După prima publicare reușită, linkul de trimis testerilor este:
<https://danie1harabagiu.github.io/flat-rubik/>.
Jocul se deschide în browser, fără Python sau cont ChatGPT.
Repository-ul trebuie să permită GitHub Pages pentru planul folosit;
pentru GitHub Free, folosește un repository public.
Salvările personale nu sunt incluse în pachetul publicat.

## Proporțiile desenului Flat Rubik

Butonul **Forma** sau tasta **T** schimbă între patru opțiuni:
**1:1** păstrează proporțiile, **Lat** lărgește desenul cu 40%, **Înalt** îl
alungește cu 40%, iar **X/Y** adaptează independent lățimea și înălțimea la
spațiul disponibil în fereastră. Aceste opțiuni afectează exclusiv desenul
Flat Rubik. Cubul 3D își păstrează proporțiile și dimensiunea zonei sale.
Formatul implicit este **X/Y**; după ce alegi alt format, aplicația îl reține.
Clicurile, săgețile și editorul de culori urmăresc aceeași transformare.
Contururile, suprafețele și săgețile sunt desenate direct la rezoluția finală,
prin transformarea coordonatelor; nu se mărește o imagine de rezoluție mică.

## Rezolvare și buget de căutare

Apasă **Rezolvare** sau **S** pentru cubul clasic de 90°. Introdu bugetul în
secunde (1–3600, implicit 30), apoi apasă **Caută**. Timpul include pregătirea
motorului și căutarea; **Oprește** permite întreruperea mai devreme.

Se numără rotațiile de 90°: o rotație de 180° costă doi pași și apare ca două
rotații distincte în plan. **Pas** / săgeata dreapta execută următoarea mutare,
iar **Automat** redă planul la viteza selectată. În timpul redării, bara de jos
lasă cubul vizibil; **Plan** revine la lista completă și la configurarea căutării.

**Optim demonstrat** înseamnă că nu există o soluție cu mai puțini pași în
această metrică. Dacă bugetul expiră înaintea demonstrației, se păstrează
cea mai scurtă soluție verificată dintre cele găsite și se precizează că
optimul nu este demonstrat. Un buget prea mic poate expira și fără soluție;
poți relua cu mai mult timp. Căutarea exactă a cuburilor foarte amestecate
poate necesita mult timp: bugetul nu garantează demonstrarea optimului.

Pe desktop, un proces separat permite oprirea calculului la expirarea
bugetului fără blocarea interfeței. Motorul în două faze din
[rubik-solver-py](https://github.com/mrrtmob/rubik-solver-py) oferă candidați,
verificați și numărați în rotații de 90°; algoritmul propriu de căutare exactă
este cel care certifică minimul. Prima utilizare poate consuma o parte
semnificativă din buget pentru pregătire; datele se păstrează local în
`.solver_cache/`, ignorat de Git. Instalează dependențele din `requirements.txt`.
În browser, motorul rapid [cube.js](https://github.com/ldez/cubejs), sub licență
MIT, rulează local într-un Web Worker. Poate rezolva și cuburi încărcate din
salvare sau introduse manual, fără istoric de mutări și fără trimiterea
configurației la un server. Fiecare candidat este verificat pe modelul jocului;
căutarea exactă continuă în porții scurte pentru a demonstra minimul în buget.
Fișierele motorului sunt incluse în pachet, cu licența și revizia sursei în `web`.

## Alegerea modului: Rubik 90° sau Puzzle 45°

La prima pornire este ales **Rubik 90°**, cu mecanica cubului fizic;
la deschiderile următoare se reia modul ales ultima dată.
Butonul **Mod: 90°** comută la **Puzzle 45°** și invers.
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
La următoarea deschidere restaurează pozițiile, vitezele și modul ales.
O animație în curs și mutările încă în coadă nu sunt salvate: se păstrează
ultima poziție completă. Fișierul sesiunii este local și ignorat de Git.

Preferințele sunt salvate separat în `puzzle_settings.json`: forma desenului
(implicit X/Y), vederea Cerc/Cub/Ambele, modul 90°/45°, butoanele vizibile,
traseele, pauza, vitezele ambelor jocuri, orientarea camerei și bugetul de
căutare. Pe calculator se rețin și dimensiunea ferestrei și ecranul complet.
În browser se folosește spațiul ferestrei curente, iar preferințele se păstrează
în stocarea locală a browserului, separat pentru fiecare site și dispozitiv.
Setările se salvează automat la modificare; fișierul nu este inclus în Git sau
în versiunea publicată. Salvările mai vechi fără preferințe pornesc în X/Y.

## Comenzi

Pe fiecare centru fix sunt două săgeți: **←** rotește fața în sens invers,
iar **→** în sens orar, privind fața din exterior. Ambele se activează cu
clic stânga și folosesc pasul modului activ (90° sau 45°).

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
| H | Ascunde / afișează panoul de butoane; desenul ocupă spațiul disponibil |
| V | Comută între Cerc, Cub 3D și Ambele |
| F11 | Ecran complet / fereastră pe laptop; Esc revine din ecran complet |
| P | Pauză / continuare |
| + / - | Mărește / micșorează durata rotației |
| E | Deschide editorul „Culori”; în editor renunță la modificări |

F = roșu, B = portocaliu, U = galben, R = verde, D = alb, L = albastru.
Clicurile funcționează pe cercul roșu, inelul portocaliu și cele patru
centre laterale de o singură culoare. Centrele au săgeți pentru cele două
sensuri de rotație, fără litere. Clicurile pe piesele mobile sau în
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
Butonul mic din stânga sus ascunde și afișează panoul inclusiv prin atingere.
Rotațiile prin săgețile centrelor și comenzile de tastatură rămân disponibile
când panoul este ascuns.

Vederea **Ambele** afișează cercul și cubul Rubik 3D sincronizate, inclusiv
în timpul rotațiilor, pauzei și amestecării. Butonul **Vedere** din partea
de sus comută între Cerc, Cub și Ambele, inclusiv pe telefon. Trage pe cub
cu mouse-ul sau degetul pentru a vedea celelalte fețe; acest gest schimbă
doar unghiul de privire. Un clic stânga sau o atingere scurtă pe o față a
cubului o rotește în sens orar; clic dreapta rotește în sens invers.
Poți folosi și panoul, săgețile cercului sau tastatura.
Pe telefon, în Ambele, vederile se așază vertical.
Editorul de culori și puzzle-ul experimental de 45° folosesc cercul;
vederea 3D reprezintă modul Rubik de 90°.

## Introducerea culorilor cubului fizic

Apasă **E** și dă clic pe suprafața pe care vrei s-o colorezi.
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
vitezei, pauză, amestecare și resetare. Butoanele Culori și Trasee nu mai apar
în panoul principal. Clic stânga/dreapta pe butoanele fețelor
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

Centrul roșu are raza de bază 44, iar piesele interioare încep la raza 46,
pentru laturi mai late spre centru. Inelul portocaliu ocupă razele 300–330, mai îngust
pentru a reduce greutatea vizuală a exteriorului.
Centrele laterale ocupă pozițiile cardinale ale rândului mijlociu,
între razele 131–205, cu deschidere de 44,5°. Galbenul este sus, verdele în
dreapta, albul jos și albastrul în stânga, conform fotografiei.

Fiecare cubuleț mobil ocupă o singură regiune compusă: două culori pentru
muchii, trei pentru colțuri. La interior, roșul ocupă partea apropiată de
centru; la exterior, portocaliul ocupă partea apropiată de inel. La colțuri
și la muchiile diagonale, culorile laterale împart lățimea regiunii. Cele
48 de suprafețe mobile aparțin celor 20 de cubulețe mobile.

La dimensiunea 800×800, rândurile mobile ocupă razele 46–129, 131–205 și
207–298. Spațiile radiale sunt de 2 pixeli, inclusiv lângă centrul roșu și
inelul exterior. Între piesele vecine rămân doar 0,5°: piesele aproape se ating,
iar conturul fin le păstrează distincte. Aceleași dimensiuni se folosesc în
animații, pentru a păstra continuitatea la începutul și sfârșitul mutării.
Separarea roșu/lateral este la raza 88, iar separarea
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

## Formă de pătrat rotunjit

Afișarea extinde zonele diagonale pentru un centru și piese mai pătrățoase.
Aceeași transformare se aplică pieselor, contururilor și animațiilor; clicurile
și editorul de culori urmăresc forma afișată.
