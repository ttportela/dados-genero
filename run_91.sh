python -u main.py terrarica --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/terrarica.txt
python -u main.py terraroxa --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/terraroxa.txt
python -u main.py tibagi --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/tibagi.txt
python -u main.py tijucasdosul --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/tijucasdosul.txt
