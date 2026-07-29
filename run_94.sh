python -u main.py umuarama --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/umuarama.txt
python -u main.py uniflor --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/uniflor.txt
python -u main.py urai --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/urai.txt
python -u main.py wenceslaubraz --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/wenceslaubraz.txt
