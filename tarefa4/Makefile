CC      = gcc
CFLAGS  = -O2 -fopenmp -Wall -Wextra
LDFLAGS = -lm

BINS = memory_bound compute_bound

all: $(BINS)

memory_bound: memory_bound.c
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS)

compute_bound: compute_bound.c
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS)

run: all
	@echo "=== Memory-bound ==="
	./memory_bound
	@echo ""
	@echo "=== Compute-bound ==="
	./compute_bound

clean:
	rm -f $(BINS)

.PHONY: all run clean
