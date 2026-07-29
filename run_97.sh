python -u main.py centenariodosul --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/centenariodosul.txt
python -u main.py lapa --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/lapa.txt
python -u main.py lidianopolis --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/lidianopolis.txt
python -u main.py marechalcandidorondon --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/marechalcandidorondon.txt
