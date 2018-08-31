create_project echo build/echo/vivado -part xc7z020clg484-1

add_files -norecurse {build/echo/echo_fill_void_priority_mux.sv build/echo/echo_fill_void_union_collapse.sv build/echo/echo.sv build/echo/wrap_echo.sv build/echo/echo_fill_void.sv build/echo/echo_cast_dout.sv build/echo/echo_fill_void_union_collapse_sieve_0.sv}
add_files -norecurse {../../svlib/dti.sv ../../svlib/add.sv ../../svlib/mul.sv ../../svlib/shr.sv}
add_files -norecurse {../../svlib/bc.sv ../../svlib/connect.sv ../../svlib/fifo.sv ../../svlib/decoupler.sv ../../svlib/sustain.sv}

update_compile_order -fileset sources_1

launch_runs impl_1

wait_on_run impl_1

open_run impl_1

report_utilization -file build/echo/echo_utilization.txt -hierarchical
