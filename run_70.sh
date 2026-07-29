python -u main.py quatrobarras --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/quatrobarras.txt
python -u main.py quatropontes --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/quatropontes.txt
python -u main.py quedasdoiguacu --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/quedasdoiguacu.txt
python -u main.py querenciadonorte --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/querenciadonorte.txt
