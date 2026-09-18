@echo off
REM ============================================================================
REM Lansator CURAT pentru training — forteaza RUN6_FRESH=0 ca sa NU porneasca
REM din BC (ar pierde antrenarea). Reia din ultimul checkpoint (modelul de boss).
REM Foloseste ASTA in loc de "python train.py" ca sa nu mai prinzi env var-uri
REM ramase din sesiuni vechi.
REM ============================================================================
cd /d "C:\LICENTA FINALA\AI_Training"
set "RUN6_FRESH=0"
set "RUN6_FRAME_STACK="
echo === Training RESUME (NU fresh) din ultimul checkpoint de boss ===
python train.py
pause
