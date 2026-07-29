python -u main.py altamiradoparana --sem-limite --etapa 1 --max-profundidade 10 --reprocessar-erros 2>&1 | tee -a resultados/_logs/altamiradoparana.txt
python -u main.py altonia --sem-limite --etapa 1 --max-profundidade 10 --reprocessar-erros 2>&1 | tee -a resultados/_logs/altonia.txt
python -u main.py altoparana --sem-limite --etapa 1 --max-profundidade 10 --reprocessar-erros 2>&1 | tee -a resultados/_logs/altoparana.txt
python -u main.py altopiquiri --sem-limite --etapa 1 --max-profundidade 10 --reprocessar-erros 2>&1 | tee -a resultados/_logs/altopiquiri.txt
