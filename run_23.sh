python -u main.py cruzeirodooeste --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/cruzeirodooeste.txt
python -u main.py cruzeirodosul --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/cruzeirodosul.txt
python -u main.py cruzmachado --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/cruzmachado.txt
python -u main.py cruzmaltina --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/cruzmaltina.txt
