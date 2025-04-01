# Use the NVIDIA TensorFlow image as the base
FROM nvcr.io/nvidia/pytorch:23.02-py3

# Set environment variables to configure tzdata non-interactively
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

# Set the working directory in the container
WORKDIR /app

COPY ./ /app/

RUN apt-get update && apt-get install -y \
            build-essential \
            cmake \
            git \
            ninja-build \
            libglib2.0-0 \
            libsm6 \
            libxext6 \
            libxrender-dev \
            tzdata

RUN pip install -r requirements/build.txt
#RUN python setup.py develop

#RUN git clone https://github.com/zhengyb/conditional-lane-detection.git


#RUN cd conditional-lane-detection \
#    && pip install -r requirements/build.txt \
#    && python setup.py develop

CMD ["bash"]





