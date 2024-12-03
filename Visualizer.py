import matplotlib.pyplot as plt

# Create a figure and axis
fig, ax = plt.subplots()

for i in range(30):
	for j in range(10):
		circle = plt.Circle((i, j), 0.4, fill=False)
		ax.add_patch(circle)


# Set axis limits and show the plot
ax.set_xlim(-1, 30)
ax.set_ylim(-1, 10)
plt.axis('equal')  # To ensure the aspect ratio is maintained
plt.show()
