CC     = gcc
CFLAGS = -Wall -std=c11
SRC    = ilp.c

all: ilp_O0 ilp_O2 ilp_O3

ilp_O0: $(SRC)
	$(CC) $(CFLAGS) -O0 -o $@ $<

ilp_O2: $(SRC)
	$(CC) $(CFLAGS) -O2 -o $@ $<

ilp_O3: $(SRC)
	$(CC) $(CFLAGS) -O3 -o $@ $<

run: all
	@echo "=== O0 ===" && ./ilp_O0
	@echo "=== O2 ===" && ./ilp_O2
	@echo "=== O3 ===" && ./ilp_O3

clean:
	rm -f ilp_O0 ilp_O2 ilp_O3
