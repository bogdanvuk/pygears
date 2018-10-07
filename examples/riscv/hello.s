;; # Very simple assembly program that will cause Spike to terminate gracefully.

.text
  .global _start

_start:

  ;; # The actual instruction I'd like to test.
  li a1, 1

  ;; # Write the value 1 to tohost, telling Spike to quit with an exit code of 0.
  li t0, 1
  la t1, tohost
  sw t0, 0(t1)

  ;; # Spin until Spike terminates the simulation.
  1: j 1b

;; # Expose tohost and fromhost to Spike so we can communicate with it.
.data
  .global tohost
tohost:   .dword 0
  .global fromhost
fromhost: .dword 0
