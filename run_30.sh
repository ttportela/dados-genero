python -u main.py fozdoiguacu --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/fozdoiguacu.txt
python -u main.py franciscoalves --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/franciscoalves.txt
python -u main.py franciscobeltrao --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/franciscobeltrao.txt
python -u main.py fozdojordao --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/fozdojordao.txt
