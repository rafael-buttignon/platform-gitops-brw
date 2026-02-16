echo "Processos usando a porta 8080:"
sudo lsof -i :8080

read -p "Deseja matar todos os processos na porta 8080? (s/n): " resp
if [[ "$resp" == "s" || "$resp" == "S" ]]; then
  for pid in $(sudo lsof -t -i :8080); do
    echo "Matando processo $pid"
    sudo kill -9 $pid
  done
  echo "Todos os processos na porta 8080 foram finalizados."
else
  echo "Nenhum processo foi finalizado."
fi