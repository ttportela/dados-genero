python -u main.py alvoradadosul --sem-limite --etapa 1 --max-profundidade 10 --reprocessar-erros 2>&1 | tee -a resultados/_logs/alvoradadosul.txt
python -u main.py amapora --sem-limite --etapa 1 --max-profundidade 10 --reprocessar-erros 2>&1 | tee -a resultados/_logs/amapora.txt
python -u main.py ampere --sem-limite --etapa 1 --max-profundidade 10 --reprocessar-erros 2>&1 | tee -a resultados/_logs/ampere.txt
python -u main.py anahy --sem-limite --etapa 1 --max-profundidade 10 --reprocessar-erros 2>&1 | tee -a resultados/_logs/anahy.txt
