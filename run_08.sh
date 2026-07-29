python -u main.py bandeirantes --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/bandeirantes.txt
python -u main.py barbosaferraz --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/barbosaferraz.txt
python -u main.py barracao --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/barracao.txt
python -u main.py barradojacare --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/barradojacare.txt
