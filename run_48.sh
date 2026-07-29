python -u main.py lupionopolis --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/lupionopolis.txt
python -u main.py mallet --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/mallet.txt
python -u main.py mambore --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/mambore.txt
python -u main.py mandaguacu --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/mandaguacu.txt
