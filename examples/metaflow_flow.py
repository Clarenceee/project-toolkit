from metaflow import FlowSpec

from reusable_helpers.workflows.metaflow.decorators import kubernetes_step


class ExampleFlow(FlowSpec):
    @kubernetes_step()
    def start(self):
        self.message = "Hello from Project Toolkit"
        self.next(self.end)

    @kubernetes_step()
    def end(self):
        print(self.message)


if __name__ == "__main__":
    ExampleFlow()
