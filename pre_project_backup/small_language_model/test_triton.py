{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "initial_id",
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "import torch\n",
    "import triton\n",
    "import triton.language as tl\n",
    "\n",
    "@triton.jit\n",
    "def add_kernel(x_ptr, y_ptr, output_ptr, n_elements, BLOCK_SIZE: tl.constexpr):\n",
    "    pid = tl.program_id(axis=0)\n",
    "    block_start = pid * BLOCK_SIZE\n",
    "    offsets = block_start + tl.arange(0, BLOCK_SIZE)\n",
    "    mask = offsets < n_elements\n",
    "    x = tl.load(x_ptr + offsets, mask=mask)\n",
    "    y = tl.load(y_ptr + offsets, mask=mask)\n",
    "    output = x + y\n",
    "    tl.store(output_ptr + offsets, output, mask=mask)\n",
    "\n",
    "def add(x: torch.Tensor, y: torch.Tensor):\n",
    "    output = torch.empty_like(x)\n",
    "    n_elements = output.numel()\n",
    "    grid = lambda meta: (triton.cdiv(n_elements, meta[\"BLOCK_SIZE\"]),)\n",
    "    add_kernel[grid](x, y, output, n_elements, BLOCK_SIZE=1024)\n",
    "    return output\n",
    "\n",
    "a = torch.rand(3, device=\"cuda\")\n",
    "b = a + a\n",
    "b_compiled = add(a, a)\n",
    "print(b_compiled - b)\n",
    "print(\"If you see tensor([0., 0., 0.], device='cuda:0'), then it works\")"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 2
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython2",
   "version": "2.7.6"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}
