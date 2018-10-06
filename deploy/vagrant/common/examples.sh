if [ -f /home/vagrant/.pygears/tools/tools.sh ]; then
    source /home/vagrant/.pygears/tools/tools.sh
fi

python3 pygears/examples/echo/plop_test_wav_echo_sim.py

exit $?
