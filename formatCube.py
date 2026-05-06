import matplotlib.pyplot as plt 
import numpy as np 

axes = (5,5,5)
data = np.ones(axes, dtype=bool)
alpha = 0.9 
colors = np.empty(axes + (4,), dtype=np.float32)
colors[:] = [1,0,0, alpha] #vermelho (altera a cor do cubo)
flg = plt.figure()
ax = flg.add_subplot(111, projection='3d')
ax.voxels(data, facecolors=colors, edgecolors='pink')
ax.view_init(30, 30)
plt.show()