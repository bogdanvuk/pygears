set common_dir [lindex $argv 0]
puts ${common_dir}

create_project echo build/echo/vivado -part xc7z020clg484-1

add_files -norecurse {build/echo/echo_fill_void_priority_mux.sv build/echo/echo_fill_void_union_collapse.sv build/echo/echo.sv build/echo/wrap_echo.sv build/echo/echo_fill_void.sv build/echo/echo_cast_dout.sv build/echo/echo_fill_void_union_collapse_sieve_0.sv}
add_files -norecurse ${common_dir}/dti.sv ${common_dir}/add.sv ${common_dir}/mul.sv ${common_dir}/shr.sv
add_files -norecurse ${common_dir}/bc.sv ${common_dir}/connect.sv ${common_dir}/fifo.sv ${common_dir}/decoupler.sv ${common_dir}/sustain.sv

update_compile_order -fileset sources_1

launch_runs impl_1

wait_on_run impl_1

open_run impl_1

report_utilization -file build/echo/echo_utilization.txt -hierarchical
