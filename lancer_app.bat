@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================================
echo   Diagnostic financier - demarrage du serveur local
echo ============================================================
echo.
echo   Adresse a ouvrir dans le navigateur :
echo.
echo       http://localhost:8501
echo.
echo   Attention : c'est bien "http" et non "https".
echo   Pour arreter le serveur : fermez cette fenetre ou Ctrl+C.
echo.
echo ============================================================
echo.

python -m streamlit run app.py --server.port 8501 --server.address localhost --browser.gatherUsageStats false

echo.
echo Le serveur s'est arrete.
pause
