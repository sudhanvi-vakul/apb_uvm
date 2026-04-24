# Run simulation
run -all

# Attempt to save coverage
coverage save coverage.ucdb

# Try to generate report (may not work)
coverage report -detail -cvg -file coverage.txt

# Exit
quit -f