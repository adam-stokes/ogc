FROM golang:1.21 AS build-stage

WORKDIR /app
COPY . ./

RUN cd ./systemtest/cmd/apmsoak/ && CGO_ENABLED=0 GOOS=linux go build -o /apmsoak .

# make image smaller
FROM gcr.io/distroless/base-debian11 AS build-release-stage

WORKDIR /

COPY --from=build-stage /apmsoak /apmsoak

ENTRYPOINT [ "/apmsoak" ]

