/**
 * @file triple_buffer.c
 * @brief Lock-free, zero-copy triple buffer implementation
 * 
 * @compliance DO-178C DAL A: REQ-FADEC-013
 * @standard MISRA C:2012
 */

#include "triple_buffer.h"
#include <string.h>

void triple_buffer_init(TripleBuffer_t *tb) {
    if (tb != (void*)0) {
        memset(tb->buffers, 0, sizeof(tb->buffers));
        atomic_init(&tb->write_idx, 0);
        atomic_init(&tb->read_idx, 1);
        atomic_init(&tb->new_idx, 2);
    }
}

bool triple_buffer_write(TripleBuffer_t *tb, const uint8_t *data, uint16_t size) {
    bool status = false;
    if ((tb != (void*)0) && (data != (void*)0) && (size <= TRIPLE_BUF_SIZE)) {
        int w = atomic_load(&tb->write_idx);
        (void)memcpy(tb->buffers[w], data, (size_t)size);

        /* Exchange current write buffer with new_idx */
        int old_new = atomic_exchange(&tb->new_idx, w);

        /* Set next write index to old new_idx buffer */
        atomic_store(&tb->write_idx, old_new);
        status = true;
    }
    return status;
}

bool triple_buffer_read(TripleBuffer_t *tb, uint8_t *data, uint16_t size) {
    bool is_new = false;
    if ((tb != (void*)0) && (data != (void*)0) && (size <= TRIPLE_BUF_SIZE)) {
        int r = atomic_load(&tb->read_idx);
        int latest_new = atomic_exchange(&tb->new_idx, r);

        if (latest_new == r) {
            /* No new data was written, copy current read buffer */
            (void)memcpy(data, tb->buffers[r], (size_t)size);
            is_new = false;
        } else {
            /* New data is available, update read index and copy */
            atomic_store(&tb->read_idx, latest_new);
            (void)memcpy(data, tb->buffers[latest_new], (size_t)size);
            is_new = true;
        }
    }
    return is_new;
}
