CC      = gcc
CFLAGS  = -O2 -fopenmp -Wall -Wextra
LDFLAGS = -lm

all: sync

sync: sync.c
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS)

run: sync
	./sync

clean:
	rm -f sync

.PHONY: all run clean
