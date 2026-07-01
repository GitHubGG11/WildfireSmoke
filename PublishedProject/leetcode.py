nums=[9,10,9,-7,-4,-8,2,-6]
k=5
heap = []
nt = len(nums)

def add_heap(heap, add, i, o):

    heap += [(add, o)]
    print(heap, "adding", i)
    while i > 0:
        print("looping")
        if i % 2 == 0:
            parent = (i - 2)/2
        else:
            parent = (i-1)/2
        
        parent = int(parent)

        print(heap[parent], parent, heap[i], i)
        if heap[parent][0] < heap[i][0]:
            temp = heap[parent]
            heap[parent] = heap[i]
            heap[i] = temp
            i = parent
        else:
            break
    print(heap, "done")


def remove_head(heap, n):

    heap[0] = heap[-1]
    heap.pop()
    j = 0

    while j*2+2 < n-1:
        if heap[2*j+1][0] > heap[2*j+2][0]:
            ind = 2*j+1
        else:
            ind = 2*j+2
        if heap[j][0] < heap[ind][0]:
            temp = heap[ind]
            heap[ind] = heap[j]
            heap[j] = temp
            j = ind
        else:
            break

for i in range(k):
    add_heap(heap, nums[i], i, i)

    print(heap)
re = []
l = k
for i in range(k, nt):
    print(heap)
    while heap[0][1] < i - k:
        print(heap[0][1], i - k)
        remove_head(heap, l)
        l -= 1

    print(heap, l, i, i-k)

    re.append(heap[0][0])
    add_heap(heap, nums[i], l, i)
    l += 1

while heap[0][1] < nt - k:
    remove_head(heap, l)
    l -= 1
print(heap)
re += [heap[0][0]]

print(heap, re)