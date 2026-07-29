python -u main.py reserva --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/reserva.txt
python -u main.py reservadoiguacu --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/reservadoiguacu.txt
python -u main.py ribeiraoclaro --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/ribeiraoclaro.txt
python -u main.py ribeiraodopinhal --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/ribeiraodopinhal.txt
