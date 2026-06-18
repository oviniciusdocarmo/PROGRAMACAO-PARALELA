CC      = gcc
CFLAGS  = -O2 -fopenmp -Wall -Wextra
LDFLAGS =

all: critical

critical: critical.c
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS)

run: critical
	./critical

clean:
	rm -f critical

.PHONY: all run clean
