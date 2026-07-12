/**
 * @file triple_buffer.h
 * @brief Lock-free, zero-copy triple buffer for real-time IPC
 * 
 * @compliance DO-178C DAL A
 * @standard MISRA C:2012
 */

#ifndef TRIPLE_BUFFER_H
#define TRIPLE_BUFFER_H

#include <stdint.h>
#include <stdbool.h>
#include <stdatomic.h>

#define TRIPLE_BUF_SIZE 256

typedef struct {
    uint8_t buffers[3][TRIPLE_BUF_SIZE];
    atomic_int write_idx;  /* index of buffer currently being written */
    atomic_int read_idx;   /* index of buffer currently being read */
    atomic_int new_idx;    /* index of most recently completed write */
} TripleBuffer_t;

/**
 * @brief Initialize a triple buffer
 */
void triple_buffer_init(TripleBuffer_t *tb);

/**
 * @brief Write data to the triple buffer
 * @param tb Pointer to triple buffer
 * @param data Source data buffer
 * @param size Data size (must be <= TRIPLE_BUF_SIZE)
 * @return true on success, false otherwise
 */
bool triple_buffer_write(TripleBuffer_t *tb, const uint8_t *data, uint16_t size);

/**
 * @brief Read data from the triple buffer
 * @param tb Pointer to triple buffer
 * @param data Destination data buffer
 * @param size Data size (must be <= TRIPLE_BUF_SIZE)
 * @return true if new data was read, false if no new data was available
 */
bool triple_buffer_read(TripleBuffer_t *tb, uint8_t *data, uint16_t size);

#endif /* TRIPLE_BUFFER_H */
