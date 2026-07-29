python -u main.py moreirasales --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/moreirasales.txt
python -u main.py morretes --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/morretes.txt
python -u main.py nossasenhoradasgracas --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/nossasenhoradasgracas.txt
python -u main.py novaaliancadoivai --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/novaaliancadoivai.txt
