python -u main.py quintadosol --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/quintadosol.txt
python -u main.py quitandinha --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/quitandinha.txt
python -u main.py ramilandia --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/ramilandia.txt
python -u main.py ranchoalegre --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/ranchoalegre.txt
