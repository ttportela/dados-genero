python -u main.py riobrancodosul --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/riobrancodosul.txt
python -u main.py rionegro --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/rionegro.txt
python -u main.py rolandia --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/rolandia.txt
python -u main.py roncador --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/roncador.txt
