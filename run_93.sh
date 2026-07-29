python -u main.py tuneirasdooeste --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/tuneirasdooeste.txt
python -u main.py tupassi --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/tupassi.txt
python -u main.py turvo --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/turvo.txt
python -u main.py ubirata --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/ubirata.txt
