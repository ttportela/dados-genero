python -u main.py toledo --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/toledo.txt
python -u main.py tomazina --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/tomazina.txt
python -u main.py tresbarrasdoparana --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/tresbarrasdoparana.txt
python -u main.py tunasdoparana --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/tunasdoparana.txt
