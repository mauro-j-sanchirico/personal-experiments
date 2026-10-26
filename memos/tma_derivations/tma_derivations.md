# Target Motion Analysis (TMA) Equation of Motion

## 1 Derivations in 2-Dimensional Cartesian Coordinates

### 1.1 Geometrical Setup

#### 1.1.1 Sensor and Target States

The sensor position is denoted

$$
\mathbf{s}(t) =
\begin{pmatrix}
s_x(t) \\
s_y(t)
\end{pmatrix}.
$$

The sensor velocity, $\dot{\mathbf{s}}(t) = \frac{d}{dt}\mathbf{s}(t)$, and sensor acceleration, $\ddot{\mathbf{s}}(t) = \frac{d^2}{dt^2}\mathbf{s}(t)$, are given as


$$
\dot{\mathbf{s}}(t) =
\begin{pmatrix}
\dot{s}_x(t) \\
\dot{s}_y(t)
\end{pmatrix},
\quad
\ddot{\mathbf{s}}(t) =
\begin{pmatrix}
\ddot{s}_x(t) \\
\ddot{s}_y(t)
\end{pmatrix}.
$$

Similarly, the target position is denoted

$$
\mathbf{p}(t) =
\begin{pmatrix}
p_x(t) \\
p_y(t)
\end{pmatrix}.
$$

The target velocity, $\dot{\mathbf{p}}(t) = \frac{d}{dt}\mathbf{p}(t)$, and target acceleration, $\ddot{\mathbf{p}}(t) = \frac{d^2}{dt^2}\mathbf{p}(t)$, are given as

$$
\dot{\mathbf{p}}(t) =
\begin{pmatrix}
\dot{p}_x(t) \\
\dot{p}_y(t)
\end{pmatrix},
\quad
\ddot{\mathbf{p}}(t) =
\begin{pmatrix}
\ddot{p}_x(t) \\
\ddot{p}_y(t)
\end{pmatrix}.
$$

The relative position, or reference vector, between the target and the sensor is given as

$$
\begin{aligned}
\mathbf{r}(t)
&=
\mathbf{p}(t) - \mathbf{s}(t),
\\
\begin{pmatrix}
r_x(t) \\
r_y(t)
\end{pmatrix}
&=
\begin{pmatrix}
p_x(t) - s_x(t) \\
p_y(t) - s_y(t)
\end{pmatrix}.
\end{aligned}
$$

Similarly, the relative velocity and acceleration are denoted $\dot{\mathbf{r}}$ and $\ddot{\mathbf{r}}$ respectively.

#### 1.1.2 Azimuth, Azimuth Rate, and Azimuth Acceleration

The azimuth angle, $\phi(t)$, is defined as the angle between the positive $x$-axis and the line of sight from the sensor to the target,

$$
\phi(t) = \operatorname{atan2}(r_y, r_x).
$$

Differentiating with respect to $t$ gives the azimuth rate,

$$
\dot{\phi}(t) =
\frac{r_x\dot{r}_y - r_y\dot{r}_x}
{r_x^2 + r_y^2}.
$$

In geometric vector form,

$$
\dot{\phi}(t) =
\frac{\mathbf{r} \times \dot{\mathbf{r}}}
{||\mathbf{r}||^2}.
$$

Formally, the conventional cross product produces a 3D vector, so the equation above relies on the 2D scalar cross-product convention, $\mathbf\times\mathbf \equiv a_xb_y-a_yb_x$.

The cross product term reveals that azimuth rate is highest when relative velocity is perpendicular to relative position, i.e., $\dot{\mathbf{r}}$ is normal to $\mathbf{r}$. The denominator reveals that azimuth rate grows as the norm of relative position,

$$
||r||^2 = r_x^2 + r_y^2,
$$

i.e., range squared, decreases. The equation assumes that range is non-zero. In practice, to keep calculations stable, range must be assumed larger than some minimum range, i.e.,

$$
||\mathbf{r}|| > R_\mathrm{MIN}.
$$

The azimuth acceleration, $\ddot{\phi}(t) = \frac{d^2}{dt^2}\phi(t)$, is given by

$$
\ddot{\phi}(t) =
\frac{r_x\ddot{r}_y-r_y\ddot{r}_x}
{r_x^2+r_y^2}
-
2\frac{
\left(r_x\dot{r}_x+r_y\dot{r}_y\right)
\left(r_x\dot{r}_y-r_y\dot{r}_x\right)
}{
\left(r_x^2+r_y^2\right)^2
}.
$$

In geometric vector form, using the 2D scalar cross-product convention,

$$
\ddot{\phi}(t) =
\frac{\mathbf{r}\times\ddot{\mathbf{r}}}
{\|\mathbf{r}\|^2}
-
2\frac{
\left(\mathbf{r}\cdot\dot{\mathbf{r}}\right)
\left(\mathbf{r}\times\dot{\mathbf{r}}\right)
}{
\|\mathbf{r}\|^4
}.
$$

Substituting the first-derivative relationship, $\dot{\phi}(t) = \frac{\mathbf{r}\times\dot{\mathbf{r}}}{||\mathbf{r}||^2}$, gives

$$
\ddot{\phi} =
\frac{\mathbf{r}\times\ddot{\mathbf{r}}}
{\|\mathbf{r}\|^2}
-
2\frac{\mathbf{r}\cdot\dot{\mathbf{r}}}
{\|\mathbf{r}\|^2}\dot{\phi}(t).
$$

### 1.2 Line of Sight (LOS) Vector

### 1.3 Range Equation and Derivatives

#### 1.3.1 Range

#### 1.3.2 Range Rate

#### 1.3.3 Range Acceleration

### 1.4 LOS and Transverse Differential Equations

#### 1.4.1 Instantaneous LOS-Transverse Coordinate Frame

#### 1.4.2 LOS Equation

#### 1.4.3 Transverse Equation

#### 1.4.4 Matrix Form

## 2 Derivations for 3-Dimensional Cartesian Coordinates

### 2.1 Geometrical Setup

#### 2.1.1 Sensor Position

#### 2.1.2 Target Position

#### 2.1.3 Relative Position

#### 2.1.4 Azimuth

#### 2.1.5 Azimuth Rate

#### 2.1.6 Azimuth Acceleration

#### 2.1.7 Elevation

#### 2.1.8 Elevation Rate

#### 2.1.9 Elevation Acceleration

### 2.2 Line of Sight (LOS) Vector

### 2.3 Range Equation and Derivatives

#### 2.3.1 Range

#### 2.3.2 Range Rate

#### 2.3.3 Range Acceleration

### 2.4 LOS and Transverse Differential Equations

#### 2.4.1 Instantaneous LOS-Transverse Coordinate Frame

#### 2.4.2 LOS Equation

#### 2.4.3 Transverse Equation

#### 2.4.4 Matrix Form

## 3 Table of Symbols

