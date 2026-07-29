python -u main.py engenheirobeltrao --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/engenheirobeltrao.txt
python -u main.py esperancanova --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/esperancanova.txt
python -u main.py entreriosdooeste --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/entreriosdooeste.txt
python -u main.py espigaoaltodoiguacu --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/espigaoaltodoiguacu.txt
