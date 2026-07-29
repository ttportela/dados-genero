python -u main.py primeirodemaio --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/primeirodemaio.txt
python -u main.py prudentopolis --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/prudentopolis.txt
python -u main.py quartocentenario --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/quartocentenario.txt
python -u main.py quatigua --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/quatigua.txt
