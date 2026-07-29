python -u main.py rondon --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/rondon.txt
python -u main.py rosariodoivai --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/rosariodoivai.txt
python -u main.py sabaudia --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/sabaudia.txt
python -u main.py salgadofilho --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/salgadofilho.txt
