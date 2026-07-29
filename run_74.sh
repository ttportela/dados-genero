python -u main.py rioazul --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/rioazul.txt
python -u main.py riobom --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/riobom.txt
python -u main.py riobonitodoiguacu --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/riobonitodoiguacu.txt
python -u main.py riobrancodoivai --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/riobrancodoivai.txt
